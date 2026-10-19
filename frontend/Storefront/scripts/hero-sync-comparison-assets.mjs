import { copyFileSync, mkdirSync, readdirSync, unlinkSync } from "node:fs";
import { join } from "node:path";

const auditRoot = join(process.cwd(), "../../audit/hero-image-quality-20261019");
const beforeDir = join(auditRoot, "browser-capture/before-main");
const afterDir = join(auditRoot, "browser-capture/after-fix");
const desktopOut = join(auditRoot, "05_BEFORE_AFTER_DESKTOP");
const mobileOut = join(auditRoot, "06_BEFORE_AFTER_MOBILE");

const desktopLabels = ["1440x900@2", "1920x1080@2", "1024x768@2", "1023x900@2"];
const mobileLabels = ["390x844@3"];
const ids = ["H01", "H02", "H03", "H04", "H05"];

function syncPair(outDir, label, id, boundary) {
  mkdirSync(outDir, { recursive: true });
  const base = `${label}_${id}`;
  const suffix = boundary && id === "H01" ? "_boundary" : "";
  copyFileSync(join(beforeDir, `${base}.png`), join(outDir, `before_${label}${suffix}_${id}.png`));
  copyFileSync(join(afterDir, `${base}.png`), join(outDir, `after_${label}${suffix}_${id}.png`));
}

for (const label of desktopLabels) {
  for (const id of ids) {
    syncPair(desktopOut, label, id, label.startsWith("1023") || label.startsWith("1024"));
  }
}
for (const label of mobileLabels) {
  for (const id of ids) {
    syncPair(mobileOut, label, id, false);
  }
}
console.log("Synced comparison PNGs from browser-capture matrices");
