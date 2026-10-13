#!/usr/bin/env bash
# Validate allowlisted read-only audit scripts changed on this PR (syntax + ruff + optional tests).
set -euo pipefail

SCRIPTS_JSON="${1:-[]}"
if [[ "$SCRIPTS_JSON" == "[]" || -z "$SCRIPTS_JSON" ]]; then
  echo "No read-only audit scripts to validate."
  exit 0
fi

mapfile -t SCRIPTS < <(python3 -c 'import json,sys; print("\n".join(json.loads(sys.argv[1])))' "$SCRIPTS_JSON")

python3 -m pip install --quiet ruff

for script in "${SCRIPTS[@]}"; do
  if [[ ! -f "$script" ]]; then
    echo "Missing script: $script" >&2
    exit 1
  fi
  echo "py_compile: $script"
  python3 -m py_compile "$script"
  echo "ruff: $script"
  ruff check "$script"
done

export SCRIPTS_JSON
mapfile -t TEST_FILES < <(python3 << 'INNER'
import json
import os
from pathlib import Path

policy = json.loads(Path(".github/ci/policy.json").read_text())
tests_map = policy.get("readonly_audit_script_tests", {})
scripts = json.loads(os.environ["SCRIPTS_JSON"])
seen: list[str] = []
for script in scripts:
    for rel in tests_map.get(script, []):
        if Path(rel).is_file() and rel not in seen:
            seen.append(rel)
for rel in seen:
    print(rel)
INNER
)

if ((${#TEST_FILES[@]} > 0)); then
  python3 -m pip install --quiet -r requirements-dev.txt
  echo "pytest (associated): ${TEST_FILES[*]}"
  pytest --maxfail=1 --disable-warnings "${TEST_FILES[@]}"
fi
