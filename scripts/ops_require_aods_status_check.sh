#!/usr/bin/env bash
# Require Backend CI job `aods` on the "Protect main" repository ruleset (OI-GOV-02).
#
# Cloud / bot tokens typically lack Administration scope (HTTP 403). Run this as a
# repo admin with a personal `gh` login:
#
#   gh auth login   # once, as Shebahati (admin)
#   bash scripts/ops_require_aods_status_check.sh
#
# UI alternative: https://github.com/Shebahati/Karzar/rules/19696648
#   → Required status checks → add context `aods` (keep `lint` and `test`).
#
# Verify only (no write):
#   bash scripts/ops_require_aods_status_check.sh --check

set -euo pipefail

REPO="${GITHUB_REPOSITORY:-Shebahati/Karzar}"
RULESET_ID="${KARZAR_MAIN_RULESET_ID:-19696648}"
CHECK_ONLY=0

if [[ "${1:-}" == "--check" ]]; then
  CHECK_ONLY=1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "FATAL: gh CLI required" >&2
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "FATAL: python3 required" >&2
  exit 1
fi

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT
gh api "repos/${REPO}/rulesets/${RULESET_ID}" >"$TMP"

export REPO RULESET_ID CHECK_ONLY
python3 - "$TMP" <<'PY'
import json, os, subprocess, sys

path = sys.argv[1]
check_only = os.environ.get("CHECK_ONLY") == "1"
repo = os.environ["REPO"]
ruleset_id = os.environ["RULESET_ID"]
required = ["lint", "test", "aods"]

with open(path, encoding="utf-8") as fh:
    data = json.load(fh)

rules = data.get("rules") or []
rsc = None
for rule in rules:
    if rule.get("type") == "required_status_checks":
        rsc = rule
        break

if rsc is None:
    print("FATAL: ruleset has no required_status_checks rule", file=sys.stderr)
    sys.exit(2)

params = rsc.setdefault("parameters", {})
checks = params.setdefault("required_status_checks", [])
have = [c.get("context") for c in checks if isinstance(c, dict)]
missing = [c for c in required if c not in have]

print(f"ruleset={data.get('name')!r} id={ruleset_id}")
print(f"current required checks: {have}")
print(f"target required checks:  {required}")

if not missing:
    print("OK: all target contexts already required (including aods).")
    sys.exit(0)

print(f"missing: {missing}")
if check_only:
    print("CHECK-ONLY: not updating (re-run without --check as repo admin).")
    sys.exit(3)

for ctx in required:
    if ctx not in have:
        checks.append({"context": ctx})

payload = {
    "name": data["name"],
    "target": data.get("target", "branch"),
    "enforcement": data.get("enforcement", "active"),
    "conditions": data.get("conditions"),
    "rules": rules,
}

proc = subprocess.run(
    [
        "gh",
        "api",
        "--method",
        "PUT",
        "-H",
        "Accept: application/vnd.github+json",
        "-H",
        "X-GitHub-Api-Version: 2022-11-28",
        f"repos/{repo}/rulesets/{ruleset_id}",
        "--input",
        "-",
    ],
    input=json.dumps(payload),
    text=True,
    capture_output=True,
)
sys.stdout.write(proc.stdout)
sys.stderr.write(proc.stderr)
if proc.returncode != 0:
    if "403" in proc.stderr or "Resource not accessible" in proc.stderr:
        print(
            "FATAL: this token cannot update rulesets (needs repo Administration). "
            "Run as a repo admin, or edit UI: "
            f"https://github.com/{repo}/rules/{ruleset_id}",
            file=sys.stderr,
        )
    sys.exit(proc.returncode or 1)

verify = subprocess.check_output(
    ["gh", "api", f"repos/{repo}/rulesets/{ruleset_id}"], text=True
)
vdata = json.loads(verify)
vhave = []
for rule in vdata.get("rules") or []:
    if rule.get("type") == "required_status_checks":
        vhave = [
            c.get("context")
            for c in (rule.get("parameters") or {}).get("required_status_checks") or []
            if isinstance(c, dict)
        ]
missing_after = [c for c in required if c not in vhave]
print(f"after update: {vhave}")
if missing_after:
    print(f"FATAL: still missing {missing_after}", file=sys.stderr)
    sys.exit(4)
print("OK: aods is now a required status check on Protect main.")
PY
