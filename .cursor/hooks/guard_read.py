#!/usr/bin/env python3
import json
import os
import sys

def emit(permission: str, message: str = "") -> None:
    payload = {"permission": permission}
    if message:
        payload["user_message"] = message
    json.dump(payload, sys.stdout)
    sys.stdout.write("\n")

try:
    data = json.load(sys.stdin)
except Exception:
    emit("deny", "Karzar hook: invalid file-read hook input; read blocked fail-closed.")
    raise SystemExit(0)

path = os.path.abspath(str(data.get("file_path") or ""))
name = os.path.basename(path).lower()

def is_env_secret(filename: str) -> bool:
    if not filename.startswith(".env"):
        return False
    return not filename.endswith(".example")

sensitive_names = {
    ".npmrc",
    ".pypirc",
    ".netrc",
    "id_rsa",
    "id_ed25519",
    "credentials",
    "credentials.json",
}

sensitive_suffixes = (".pem", ".key", ".p12", ".pfx")

if is_env_secret(name) or name in sensitive_names or name.endswith(sensitive_suffixes):
    emit(
        "deny",
        f"Karzar safety gate: reading sensitive credential file '{name}' is blocked.",
    )
    raise SystemExit(0)

emit("allow")
