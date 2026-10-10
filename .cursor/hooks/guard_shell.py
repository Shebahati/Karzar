#!/usr/bin/env python3
import json
import re
import sys

def emit(permission: str, message: str = "") -> None:
    payload = {"permission": permission}
    if message:
        payload["user_message"] = message
        payload["agent_message"] = message
    json.dump(payload, sys.stdout)
    sys.stdout.write("\n")

try:
    data = json.load(sys.stdin)
except Exception:
    emit("deny", "Karzar hook: invalid shell-hook input; command blocked fail-closed.")
    raise SystemExit(0)

command = str(data.get("command") or "").strip()

BLOCK_RULES = [
    (
        re.compile(r"\bgit\s+push\b[^\n]*(?:--force(?:-with-lease)?|-f(?:\s|$))", re.I),
        "Force-push is blocked. Use a normal branch push or perform the exceptional action manually.",
    ),
    (
        re.compile(r"\bgit\s+push\b[^\n]*(?:\borigin\s+)?(?:HEAD:)?main\b", re.I),
        "Direct push to main is blocked. Use a feature branch and PR.",
    ),
    (
        re.compile(r"\bgh\s+pr\s+merge\b", re.I),
        "Agent-driven PR merge is blocked. Merge requires explicit human action.",
    ),
    (
        re.compile(r"\bgit\s+reset\s+--hard\b", re.I),
        "git reset --hard is blocked to protect unrelated work.",
    ),
    (
        re.compile(r"\bgit\s+clean\b[^\n]*-\w*f\w*", re.I),
        "Forced git clean is blocked to protect untracked work.",
    ),
    (
        re.compile(r"\bKARZAR_ALLOW_PRODUCTION_WRITE\s*=\s*1\b", re.I),
        "Production-write override is blocked in Cursor Agent.",
    ),
]

for pattern, message in BLOCK_RULES:
    if pattern.search(command):
        emit("deny", f"Karzar safety gate: {message}")
        raise SystemExit(0)

if "api.karzartools.com" in command.lower():
    mutating_curl = re.search(
        r"\bcurl\b[^\n]*(?:-X|--request)\s*(POST|PUT|PATCH|DELETE)\b",
        command,
        re.I,
    )
    if mutating_curl:
        emit(
            "deny",
            "Karzar safety gate: mutating requests to api.karzartools.com are blocked in Cursor Agent.",
        )
        raise SystemExit(0)

if re.search(r"\brm\s+-rf\s+(?:/|~|\$HOME)(?:\s|$)", command):
    emit("deny", "Karzar safety gate: destructive rm -rf target is blocked.")
    raise SystemExit(0)

emit("allow")
