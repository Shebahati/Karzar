from __future__ import annotations

import argparse
import json
import os
import secrets
import stat
import sys
import webbrowser
from pathlib import Path

from services.gsc_mcp.config import GOOGLE_OAUTH_SCOPE
from services.gsc_mcp.http_google import GoogleHttpClient
from services.gsc_mcp.oauth_google import build_authorization_url, exchange_authorization_code
from services.gsc_mcp.oauth_loopback import LoopbackOAuthServer
from services.gsc_mcp.pkce import code_challenge_s256, generate_code_verifier

DEFAULT_CREDENTIALS_PATH = Path.home() / ".config" / "karzar" / "gsc" / "credentials.json"


def _load_client_from_file(path: Path) -> tuple[str, str | None]:
    data = json.loads(path.read_text(encoding="utf-8"))
    installed = data.get("installed") or data.get("web") or data
    client_id = data.get("client_id") or installed.get("client_id")
    client_secret = data.get("client_secret") or installed.get("client_secret")
    if not client_id:
        raise SystemExit("OAuth client JSON must include client_id")
    return str(client_id), str(client_secret) if client_secret else None


def write_credentials_file(
    path: Path,
    *,
    client_id: str,
    client_secret: str | None,
    refresh_token: str,
) -> None:
    payload: dict[str, str] = {
        "client_id": client_id,
        "refresh_token": refresh_token,
        "scope": GOOGLE_OAUTH_SCOPE,
    }
    if client_secret:
        payload["client_secret"] = client_secret
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def run_bootstrap(
    *,
    client_id: str,
    client_secret: str | None,
    output: Path,
    open_browser: bool = True,
    print_refresh_token: bool = False,
) -> None:
    state = secrets.token_urlsafe(32)
    code_verifier = generate_code_verifier()
    code_challenge = code_challenge_s256(code_verifier)

    loopback = LoopbackOAuthServer.start(expected_state=state)
    try:
        auth_url = build_authorization_url(
            client_id=client_id,
            redirect_uri=loopback.redirect_uri,
            state=state,
            code_challenge=code_challenge,
        )
        print("Opening browser for Google authorization (Search Console readonly scope only).")
        print(f"Requested scope: {GOOGLE_OAUTH_SCOPE}")
        if open_browser:
            webbrowser.open(auth_url)
        else:
            print("Open this URL in your browser:")
            print(auth_url)

        callback = loopback.wait_for_result(timeout_seconds=300.0)
        if callback.error or not callback.code:
            raise SystemExit(f"OAuth authorization failed: {callback.error or 'unknown'}")

        http = GoogleHttpClient(
            timeout_seconds=30.0,
            max_retries=1,
            user_agent="Karzar-GSC-MCP-bootstrap/0.1",
            token_provider=None,
        )
        token_response = exchange_authorization_code(
            client_id=client_id,
            client_secret=client_secret,
            code=callback.code,
            redirect_uri=loopback.redirect_uri,
            code_verifier=code_verifier,
            http=http,
        )
    finally:
        loopback.shutdown()

    refresh = token_response.get("refresh_token")
    if not refresh:
        raise SystemExit(
            "No refresh_token in response. Re-run bootstrap; ensure prompt=consent and access_type=offline."
        )

    if print_refresh_token:
        print("\nWARNING: refresh token is a secret. Do not commit or paste into chat.")
        print(refresh)
        return

    write_credentials_file(
        output,
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=str(refresh),
    )
    print(f"Wrote credentials to {output} (mode 0600). Do not commit this file.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Local-only Google GSC OAuth bootstrap (readonly scope).")
    parser.add_argument(
        "--credentials-file",
        type=Path,
        help="Desktop OAuth client JSON from Google Cloud Console",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_CREDENTIALS_PATH, help="Write refresh token here")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open a system browser; print the authorization URL instead",
    )
    parser.add_argument(
        "--print-refresh-token",
        action="store_true",
        help="Advanced: print refresh token to stdout (SECRET — do not log or commit)",
    )
    args = parser.parse_args(argv)

    client_id = os.environ.get("GOOGLE_GSC_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_GSC_CLIENT_SECRET")
    if args.credentials_file:
        client_id, file_secret = _load_client_from_file(args.credentials_file)
        if file_secret:
            client_secret = file_secret
    if not client_id:
        raise SystemExit("Set GOOGLE_GSC_CLIENT_ID or pass --credentials-file")

    run_bootstrap(
        client_id=client_id,
        client_secret=client_secret,
        output=args.output,
        open_browser=not args.no_browser,
        print_refresh_token=args.print_refresh_token,
    )


if __name__ == "__main__":
    main(sys.argv[1:])
