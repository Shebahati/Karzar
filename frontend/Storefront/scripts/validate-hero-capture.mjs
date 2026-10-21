import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

const dir = process.argv[2];
if (!dir) {
  console.error("Usage: node scripts/validate-hero-capture.mjs <captureDir>");
  process.exit(2);
}
const labels = ["390x844@3", "1023x900@2", "1024x768@2", "1440x900@2", "1920x1080@2"];
const ids = ["H01", "H02", "H03", "H04", "H05"];
let errors = 0;
for (const label of labels) {
  for (const id of ids) {
    const base = `${label}_${id}`;
    const jsonPath = join(dir, `${base}.json`);
    const pngPath = join(dir, `${base}.png`);
    try {
      const data = JSON.parse(readFileSync(jsonPath, "utf8"));
      if (data.slideId !== id) {
        console.error(`${base}: slideId mismatch ${data.slideId}`);
        errors += 1;
      }
      if (!data.currentSrc?.includes(data.expectedAsset)) {
        console.error(`${base}: currentSrc does not include expectedAsset`);
        errors += 1;
      }
      if (!data.currentSrc?.includes("photo-20261021-v2")) {
        console.error(`${base}: not calibrated path`);
        errors += 1;
      }
      if (data.naturalWidth < 1) {
        console.error(`${base}: image not decoded`);
        errors += 1;
      }
      readFileSync(pngPath);
    } catch (e) {
      console.error(`${base}: missing or invalid`, e.message);
      errors += 1;
    }
  }
}
if (errors) {
  console.error(`FAILED: ${errors} validation error(s)`);
  process.exit(1);
}
console.log(`OK: 25 captures validated in ${dir}`);
