/**
 * LOCAL_BUILD_EVIDENCE — production standalone screenshots.
 * Prereq: Storefront build + standalone on ACCEPTANCE_BASE_URL (default :3098).
 */
import { createRequire } from "node:module";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dir = dirname(fileURLToPath(import.meta.url));
const require = createRequire(
  join(__dir, "../../frontend/Storefront/package.json"),
);
const { chromium } = require("playwright");

const BASE = process.env.ACCEPTANCE_BASE_URL ?? "http://127.0.0.1:3098";
const SHA = process.env.GIT_SHA ?? "local";

const VIEWPORTS = [
  { tag: "desktop-1366", width: 1366, height: 768, mobile: false },
  { tag: "desktop-1920", width: 1920, height: 1080, mobile: false },
  { tag: "mobile-390", width: 390, height: 844, mobile: true },
  { tag: "tablet-1023", width: 1023, height: 768, mobile: false },
];

const SLIDE_IDS = ["H01", "H02", "H03", "H04", "H05"];

async function visibleTitle(page) {
  return page.evaluate(() => {
    const hero = document.querySelector('section[aria-label="هیرو کارزار"]');
    if (!hero) return null;
    for (const el of hero.querySelectorAll("h1, h2")) {
      if (el.closest('[aria-hidden="true"]')) continue;
      const r = el.getBoundingClientRect();
      if (r.width > 0) return el.textContent?.trim();
    }
    return null;
  });
}

async function metricsForSlide(page) {
  return page.evaluate(() => {
    const hero = document.querySelector('section[aria-label="هیرو کارزار"]');
    const header = document.querySelector("header");
    const copy =
      document.querySelector('[data-testid="campaign-hero-copy-stack"]') ??
      document.querySelector('[data-testid="campaign-hero-desktop-copy-column"]');
    const h = hero?.getBoundingClientRect();
    const hd = header?.getBoundingClientRect();
    const c = copy?.getBoundingClientRect();
    const title = copy?.querySelector("h1,h2")?.getBoundingClientRect();
    return {
      hero: h ? { top: h.top, bottom: h.bottom, right: h.right, left: h.left } : null,
      header: hd ? { bottom: hd.bottom } : null,
      copy: c ? { top: c.top, right: c.right, left: c.left, width: c.width } : null,
      title: title ? { top: title.top, right: title.right } : null,
      rightSafeMargin: h && title ? h.right - title.right : null,
      headerClearance: hd && title ? title.top - hd.bottom : null,
    };
  });
}

async function main() {
  mkdirSync(__dir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const allMetrics = [];

  for (const vp of VIEWPORTS) {
    const ctx = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
      isMobile: vp.mobile,
      hasTouch: vp.mobile,
    });
    const page = await ctx.newPage();
    await page.addInitScript(() => sessionStorage.setItem("karzar-splash-seen", "1"));
    await page.goto(`${BASE}/`, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1200);

    for (let i = 0; i < 5; i += 1) {
      const title = await visibleTitle(page);
      const file = join(__dir, `${vp.tag}-${SLIDE_IDS[i]}.png`);
      await page.screenshot({ path: file, fullPage: false });
      const m = await metricsForSlide(page);
      allMetrics.push({ viewport: vp.tag, slide: SLIDE_IDS[i], title, ...m });
      if (i < 4) {
        const btn = page.getByRole("button", { name: "اسلاید بعدی" });
        await btn.click();
        await page.waitForTimeout(600);
      }
    }
    await ctx.close();
  }

  await browser.close();
  writeFileSync(join(__dir, "metrics.json"), JSON.stringify({ gitSha: SHA, slides: allMetrics }, null, 2));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
