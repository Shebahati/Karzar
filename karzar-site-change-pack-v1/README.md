# Karzar local site change pack v1

This package contains the approved hero assets, final Persian content, catalog rules, target taxonomy, and one bounded Cursor Auto implementation prompt.

## Before running Cursor

1. Extract this directory into the root of the Karzar repository so the following path exists:

   `./karzar-site-change-pack-v1/CURSOR_AUTO_PROMPT.md`

2. Paste the exact official Enamad HTML snippet into:

   `./karzar-site-change-pack-v1/enamad-snippet.html`

   Do not use a screenshot or a guessed badge URL. The official validation link and image/script supplied by Enamad must remain intact.

3. Open `CURSOR_AUTO_PROMPT.md`, copy the complete content, and paste it once into Cursor in Auto mode.

4. Let Cursor finish the single implementation run and start the local stack. Do not ask Cursor to push or deploy.

## Selected hero assets

- Six desktop PNG source images under `assets/heroes/desktop/`
- Six art-directed mobile PNG source images under `assets/heroes/mobile/`

Cursor should move/copy these assets into the repository's normal public asset location and use the project's existing image optimization pipeline to emit WebP/AVIF when supported. PNG files are the source masters.

## Rejected image

An intermediate turning-action image was rejected for questionable cutting-tool orientation and is intentionally not included.

