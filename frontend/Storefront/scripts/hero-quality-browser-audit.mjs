import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import {
  MANDATORY_VIEWPORTS,
  SLIDES,
  advanceOneSlide,
  assertActiveSlide,
  collectSlideMetrics,
  gotoHomeReady,
  installPerfInstrumentation,
} from "./hero-audit-lib.mjs";

const tag = process.argv[2];
if (!tag) {
  console.error("Usage: node scripts/hero-quality-browser-audit.mjs <before-main|after-fix> [outDir]");
  process.exit(2);
}
const outRoot =
  process.argv[3] ??
  join(process.cwd(), "../../audit/hero-image-quality-20261019/browser-capture", tag);
mkdirSync(outRoot, { recursive: true });

const browser = await chromium.launch({ channel: "chrome", headless: true });
const matrix = [];

for (const vp of MANDATORY_VIEWPORTS) {
  const context = await browser.newContext({
    viewport: { width: vp.w, height: vp.h },
    deviceScaleFactor: vp.dpr,
  });
  const page = await context.newPage();
  await installPerfInstrumentation(page);
  await gotoHomeReady(page);

  for (let index = 0; index < SLIDES.length; index += 1) {
    const { heroRegion } = await assertActiveSlide(page, index, vp.compact);
    const metrics = await collectSlideMetrics(page, index, vp.compact, vp.label);
    const fileBase = `${vp.label}_${SLIDES[index].id}`;
    writeFileSync(join(outRoot, `${fileBase}.json`), JSON.stringify(metrics, null, 2));
    await heroRegion.screenshot({ path: join(outRoot, `${fileBase}.png`) });
    matrix.push(metrics);
    if (index < SLIDES.length - 1) {
      await advanceOneSlide(page);
    }
  }
  await context.close();
}

writeFileSync(join(outRoot, "delivery-matrix.json"), JSON.stringify(matrix, null, 2));
await browser.close();
console.log(`wrote ${matrix.length} captures to ${outRoot}`);
