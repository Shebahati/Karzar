/**
 * Full-bleed five-hero geometry + screenshots (local prod build).
 *   cd frontend/Storefront && npm run build && npm run start -- -p 3010
 *   node audit/hero-fullscreen-five-2026-10-13/fullbleed-probe.mjs
 */
import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(
  path.join(path.dirname(fileURLToPath(import.meta.url)), "../../frontend/Storefront/package.json"),
);
const { chromium } = require("@playwright/test");

const OUT = path.dirname(fileURLToPath(import.meta.url));
const BASE = process.env.HERO_PROBE_BASE ?? "http://127.0.0.1:3010";
const VIEWPORTS = [
  { id: "1920x1080", w: 1920, h: 1080 },
  { id: "1440x900", w: 1440, h: 900 },
  { id: "1366x768", w: 1366, h: 768 },
  { id: "768x1024", w: 768, h: 1024 },
  { id: "390x844", w: 390, h: 844 },
];

const SLIDE_TITLES = [
  "تخفیف‌های ویژه‌ی کارزار",
  "ابزار اندازه‌گیری",
  "اینسرت و ابزارهای اینسرتی",
  "فرز انگشتی",
  "دستگاه‌های صنعتی",
];

async function measureHero(page) {
  return page.evaluate(() => {
    const hero = document.querySelector('section[aria-label="هیرو کارزار"]');
    const outer = hero?.parentElement;
    const next = outer?.nextElementSibling;
    const hr = hero?.getBoundingClientRect();
    const or = outer?.getBoundingClientRect();
    const nr = next?.getBoundingClientRect();
    const img =
      hero?.querySelector('[data-testid="campaign-hero-fullbleed"] img') ??
      hero?.querySelector("img");
    const ir = img?.getBoundingClientRect();
    const gap = hr && nr ? nr.top - hr.bottom : null;
    return {
      heroW: hr?.width ?? null,
      heroH: hr?.height ?? null,
      imageW: ir?.width ?? null,
      imageH: ir?.height ?? null,
      widthRatio: hr && ir ? ir.width / hr.width : null,
      gap,
      overlap: gap !== null && gap < -2,
      viewportH: window.innerHeight,
    };
  });
}

async function main() {
  const browser = await chromium.launch();
  const manifest = {
    kind: "fullscreen-five-hero",
    capturedAt: new Date().toISOString(),
    base: BASE,
    viewports: [],
    slides1920: [],
  };

  for (const vp of VIEWPORTS) {
    const ctx = await browser.newContext({
      viewport: { width: vp.w, height: vp.h },
      reducedMotion: "reduce",
    });
    const page = await ctx.newPage();
    await page.goto(`${BASE}/`, { waitUntil: "networkidle", timeout: 120_000 });
    await page.waitForTimeout(1200);
    const layout = await measureHero(page);
    await mkdir(path.join(OUT, "screenshots"), { recursive: true });
    await page.screenshot({ path: path.join(OUT, "screenshots", `${vp.id}-fold.png`) });
    manifest.viewports.push({ id: vp.id, layout });
    await ctx.close();
  }

  const ctx = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    reducedMotion: "reduce",
  });
  const page = await ctx.newPage();
  await page.goto(`${BASE}/`, { waitUntil: "networkidle", timeout: 120_000 });
  await page.waitForTimeout(1500);

  for (let i = 0; i < SLIDE_TITLES.length; i++) {
    const title = await page.evaluate(() => {
      const h = document.querySelector(
        'section[aria-label="هیرو کارزار"] h1, section[aria-label="هیرو کارزار"] h2',
      );
      return h?.textContent?.trim() ?? "";
    });
    const layout = await measureHero(page);
    await page.screenshot({
      path: path.join(OUT, "screenshots", `1920x1080-slide-h0${i + 1}.png`),
    });
    manifest.slides1920.push({ index: i + 1, title, layout });
    if (i < SLIDE_TITLES.length - 1) {
      await page.getByRole("button", { name: "اسلاید بعدی" }).click();
      await page.waitForTimeout(1800);
    }
  }
  await ctx.close();

  await writeFile(path.join(OUT, "manifest.json"), JSON.stringify(manifest, null, 2));
  await browser.close();
  console.log("Wrote", path.join(OUT, "manifest.json"));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
