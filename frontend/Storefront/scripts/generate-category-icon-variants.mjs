#!/usr/bin/env node
/**
 * Local build helper — generates WebP (+ optional AVIF) variants beside originals.
 * Does not delete or overwrite PNG sources.
 */
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ICON_DIR = path.join(__dirname, "../public/category-icons");
const WEBP_DIR = path.join(ICON_DIR, "webp");
const AVIF_DIR = path.join(ICON_DIR, "avif");
const MAX_EDGE = 256; // 3× for ~85px hero dock glyph

const py = `
import json, sys
from pathlib import Path
from PIL import Image

icon_dir = Path(sys.argv[1])
webp_dir = Path(sys.argv[2])
avif_dir = Path(sys.argv[3])
max_edge = int(sys.argv[4])
webp_dir.mkdir(parents=True, exist_ok=True)
avif_dir.mkdir(parents=True, exist_ok=True)
manifest = []
for png in sorted(icon_dir.glob("*.png")):
    im = Image.open(png).convert("RGBA")
    w, h = im.size
    scale = min(1.0, max_edge / max(w, h))
    if scale < 1.0:
        im = im.resize((int(w*scale), int(h*scale)), Image.Resampling.LANCZOS)
    stem = png.stem
    webp_path = webp_dir / f"{stem}.webp"
    avif_path = avif_dir / f"{stem}.avif"
    im.save(webp_path, "WEBP", quality=82, method=6, lossless=False)
    try:
        im.save(avif_path, "AVIF", quality=55)
        avif_bytes = avif_path.stat().st_size
    except Exception:
        avif_path.unlink(missing_ok=True)
        avif_bytes = None
    manifest.append({
        "file": png.name,
        "png_bytes": png.stat().st_size,
        "webp_bytes": webp_path.stat().st_size,
        "avif_bytes": avif_bytes,
        "display_max_edge_px": max_edge,
        "output_dimensions": list(im.size),
    })
print(json.dumps(manifest, indent=2))
`;

const r = spawnSync("python3", ["-c", py, ICON_DIR, WEBP_DIR, AVIF_DIR, String(MAX_EDGE)], {
  encoding: "utf8",
});
if (r.status !== 0) {
  console.error(r.stderr || r.stdout);
  process.exit(1);
}
const manifest = JSON.parse(r.stdout);
const out = path.join(__dirname, "../../../audit/performance-category-icon-experiment-2026-10-20/ASSET_MANIFEST_GENERATED.json");
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, JSON.stringify({ generated_at: new Date().toISOString(), variants: manifest }, null, 2));
console.log("Wrote", out);
let pngSum = 0, webpSum = 0;
for (const row of manifest) {
  pngSum += row.png_bytes;
  webpSum += row.webp_bytes;
}
console.log("PNG total", pngSum, "WebP total", webpSum, "reduction", ((1 - webpSum / pngSum) * 100).toFixed(1) + "%");
