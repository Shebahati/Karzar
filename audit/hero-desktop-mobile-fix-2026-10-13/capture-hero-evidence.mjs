/**
 * Heroes Reborn 5 desktop + mobile fix evidence (post #481).
 * Prefer production build: `npm run build && npm run start` in frontend/Storefront.
 *
 *   BASE_URL=http://127.0.0.1:3000 node audit/hero-desktop-mobile-fix-2026-10-13/capture-hero-evidence.mjs
 */
import { createRequire } from "node:module";
import { execSync } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(
  path.join(path.dirname(fileURLToPath(import.meta.url)), "../../frontend/Storefront/package.json"),
);
const { chromium, devices } = require("@playwright/test");

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT = __dirname;
const BASE_URL = process.env.BASE_URL ?? "http://127.0.0.1:3000";
const MOTION = process.env.HERO_MOTION ?? "no-preference";

let commitSha = "unknown";
try {
  commitSha = execSync("git rev-parse HEAD", { encoding: "utf8" }).trim();
} catch {
  /* optional */
}

const VIEWPORTS = [
  { id: "1920x1080", width: 1920, height: 1080, mobile: false },
  { id: "1440x900", width: 1440, height: 900, mobile: false },
  { id: "1366x768", width: 1366, height: 768, mobile: false },
  { id: "1363x936", width: 1363, height: 936, mobile: false },
  { id: "768x1024", width: 768, height: 1024, mobile: true },
  { id: "390x844", width: 390, height: 844, mobile: true },
  { id: "360x800", width: 360, height: 800, mobile: true },
  { id: "430x932", width: 430, height: 932, mobile: true },
];

const SLIDE_TITLES = [
  "تخفیف‌های ویژه‌ی کارزار",
  "ابزار اندازه‌گیری",
  "اینسرت و ابزارهای اینسرتی",
  "فرز انگشتی",
  "دستگاه‌های صنعتی",
];

async function waitHeroSettled(page) {
  await page.waitForSelector('section[aria-label="هیرو کارزار"]', { timeout: 60_000 });
  await page.waitForSelector('section[aria-label="هیرو کارزار"] h1, section[aria-label="هیرو کارزار"] h2', {
    timeout: 60_000,
  });
  await page
    .waitForFunction(
      () => {
        const hero = document.querySelector('section[aria-label="هیرو کارزار"]');
        const img = hero?.querySelector("img");
        return !img || (img.complete && img.naturalWidth > 0);
      },
      { timeout: 45_000 },
    )
    .catch(() => {});
  await page.waitForTimeout(1200);
}

async function swipeNext(page, box) {
  const startX = box.x + box.width * 0.78;
  const endX = box.x + box.width * 0.22;
  const y = box.y + box.height * 0.42;
  await page.touchscreen.tap(startX, y);
  await page.mouse.move(startX, y);
  await page.mouse.down();
  await page.mouse.move(endX, y, { steps: 12 });
  await page.mouse.up();
  await page.waitForTimeout(900);
}

async function captureSlides(page, vp, mobile) {
  const shots = [];
  for (let i = 0; i < SLIDE_TITLES.length; i++) {
    await waitHeroSettled(page);
    const file = path.join(OUT, "screenshots", `${vp.id}-slide-${i + 1}.png`);
    await page.screenshot({ path: file, fullPage: false });
    shots.push(file);
    if (i < SLIDE_TITLES.length - 1) {
      const hero = page.locator('section[aria-label="هیرو کارزار"]');
      const box = await hero.boundingBox();
      if (mobile && box) {
        await swipeNext(page, box);
      } else {
        await hero.getByRole("button", { name: "اسلاید بعدی" }).click();
        await page.waitForTimeout(900);
      }
    }
  }
  return shots;
}

async function main() {
  await mkdir(path.join(OUT, "screenshots"), { recursive: true });
  await mkdir(path.join(OUT, "videos"), { recursive: true });

  const browser = await chromium.launch();
  const meta = { commitSha, baseUrl: BASE_URL, motion: MOTION, viewports: [] };

  for (const vp of VIEWPORTS) {
    const contextOptions = {
      viewport: { width: vp.width, height: vp.height },
      reducedMotion: MOTION === "reduce" ? "reduce" : "no-preference",
    };
    if (vp.mobile) {
      Object.assign(contextOptions, devices["Pixel 5"]);
      contextOptions.viewport = { width: vp.width, height: vp.height };
      contextOptions.hasTouch = true;
    }
    const context = await browser.newContext(contextOptions);
    const page = await context.newPage();
    await page.goto(`${BASE_URL}/`, { waitUntil: "domcontentloaded", timeout: 120_000 });
    const shots = await captureSlides(page, vp, vp.mobile);
    meta.viewports.push({ id: vp.id, touch: vp.mobile, shots });
    await context.close();
  }

  await writeFile(
    path.join(OUT, "manifest.json"),
    JSON.stringify({ ...meta, capturedAt: new Date().toISOString() }, null, 2),
  );
  await browser.close();
  console.log("Wrote evidence to", OUT);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
