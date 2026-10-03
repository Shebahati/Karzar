from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import uuid
from pathlib import Path

from services.gsc_mcp.config import GOOGLE_OAUTH_SCOPE
from services.gsc_mcp.http_google import GoogleHttpClient
from services.gsc_mcp.oauth_google import build_authorization_url, exchange_authorization_code

DEFAULT_REDIRECT = "http://127.0.0.1:8765/oauth/callback"
DEFAULT_CREDENTIALS_PATH = Path.home() / ".config" / "karzar" / "gsc" / "credentials.json"


def _load_client_from_file(path: Path) -> tuple[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    client_id = data.get("client_id") or data.get("installed", {}).get("client_id")
    client_secret = data.get("client_secret") or data.get("installed", {}).get("client_secret")
    if not client_id or not client_secret:
        raise SystemExit("credentials file must include client_id and client_secret")
    return str(client_id), str(client_secret)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Local-only Google GSC OAuth bootstrap (readonly scope).")
    parser.add_argument("--credentials-file", type=Path, help="OAuth client JSON from Google Cloud Console")
    parser.add_argument("--output", type=Path, default=DEFAULT_CREDENTIALS_PATH, help="Write refresh token here")
    parser.add_argument("--redirect-uri", default=DEFAULT_REDIRECT)
    parser.add_argument(
        "--print-refresh-token",
        action="store_true",
        help="Print refresh token to stdout (SECRET — do not log or commit)",
    )
    parser.add_argument("--code", help="Authorization code (if already obtained)")
    args = parser.parse_args(argv)

    client_id = os.environ.get("GOOGLE_GSC_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_GSC_CLIENT_SECRET")
    if args.credentials_file:
        client_id, client_secret = _load_client_from_file(args.credentials_file)
    if not client_id or not client_secret:
        raise SystemExit("Set GOOGLE_GSC_CLIENT_ID/SECRET or pass --credentials-file")

    state = str(uuid.uuid4())
    auth_url = build_authorization_url(
        client_id=client_id,
        redirect_uri=args.redirect_uri,
        state=state,
    )
    print("Authorize this URL in a browser (readonly scope only):")
    print(auth_url)
    print(f"Requested scope: {GOOGLE_OAUTH_SCOPE}")

    code = args.code
    if not code:
        code = input("Paste authorization code: ").strip()
    if not code:
        raise SystemExit("No authorization code provided")

    http = GoogleHttpClient(
        timeout_seconds=30.0,
        max_retries=1,
        user_agent="Karzar-GSC-MCP-bootstrap/0.1",
        token_provider=None,
    )
    token_response = exchange_authorization_code(
        client_id=client_id,
        client_secret=client_secret,
        code=code,
        redirect_uri=args.redirect_uri,
        http=http,
    )
    refresh = token_response.get("refresh_token")
    if not refresh:
        raise SystemExit(
            "No refresh_token in response. Re-run with prompt=consent and ensure access_type=offline."
        )

    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh,
        "scope": GOOGLE_OAUTH_SCOPE,
    }

    if args.print_refresh_token:
        print("\nWARNING: refresh token is a secret. Do not commit or paste into chat.")
        print(refresh)
        return

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    args.output.chmod(stat.S_IRUSR | stat.S_IWUSR)
    print(f"Wrote credentials to {args.output} (mode 0600). Do not commit this file.")


if __name__ == "__main__":
    main(sys.argv[1:])
