#!/usr/bin/env bash
# Idempotently add HSTS to every HTTPS server block in the live karzar nginx site.
set -euo pipefail

CONF="${1:-/etc/nginx/sites-enabled/karzar}"
HSTS='add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;'

if [[ ! -f "$CONF" ]]; then
  echo "Missing $CONF" >&2
  exit 1
fi

if grep -q 'Strict-Transport-Security' "$CONF"; then
  echo "HSTS already present in $CONF"
  exit 0
fi

python3 - "$CONF" <<'PY'
import pathlib, re, sys
path = pathlib.Path(sys.argv[1])
text = path.read_text()
hsts = '    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;\n'
# Insert HSTS after each ssl_certificate_key line inside 443 blocks (certbot style).
pattern = re.compile(
    r'(listen 443 ssl;[^\n]*\n(?:.*\n)*?\s*ssl_certificate_key[^\n]*\n)',
    re.M,
)
def repl(m: re.Match[str]) -> str:
    block = m.group(1)
    if "Strict-Transport-Security" in block:
        return block
    return block + hsts

new, n = pattern.subn(repl, text)
if n == 0:
    # Fallback: after each "listen 443 ssl" line
    lines = text.splitlines(keepends=True)
    out = []
    for line in lines:
        out.append(line)
        if re.search(r"listen\s+443\s+ssl", line) and "Strict-Transport-Security" not in "".join(out[-5:]):
            out.append(hsts)
    new = "".join(out)
    n = new.count("Strict-Transport-Security") - text.count("Strict-Transport-Security")
path.write_text(new)
print(f"Inserted HSTS near {n} SSL listen/cert blocks in {path}")
PY

nginx -t
systemctl reload nginx
echo "Nginx reloaded with HSTS."
