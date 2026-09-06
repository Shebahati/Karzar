# Printable wallboards

## Primary (print-ready PDF)
- `PMO_31_Shahrivar_wallboard.pdf` — full PMO through 31 Shahrivar (A4 portrait, 4 pages)
- `PMO_31_Shahrivar_wallboard.html` — source; open in browser → Print

## Legacy quick boards
- `A4-portrait.html`
- `A4-landscape.html`
- `A3-landscape.html` (best for wall if regenerating single-sheet)

Use color printing for status chips and P0 bars (`#C22026`).

Regenerate PDF (from this directory):

```bash
google-chrome --headless=new --disable-gpu --no-pdf-header-footer \
  --print-to-pdf=PMO_31_Shahrivar_wallboard.pdf \
  file://$PWD/PMO_31_Shahrivar_wallboard.html
```
