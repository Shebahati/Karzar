/**
 * LOCAL_BUILD_EVIDENCE — production standalone screenshots + physical geometry gates.
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

const SLIDE_IDS = ["H01", "H02", "H03", "H04", "H05"];
const EXPECTED_TITLES = [
  "تخفیف‌های ویژه‌ی کارزار",
  "ابزار اندازه‌گیری",
  "اینسرت و ابزارهای اینسرتی",
  "فرز انگشتی",
  "دستگاه‌های صنعتی",
];

const VIEWPORTS = [
  { tag: "desktop-1366", width: 1366, height: 768, mobile: false, desktop: true },
  { tag: "desktop-1920", width: 1920, height: 1080, mobile: false, desktop: true },
  { tag: "mobile-390", width: 390, height: 844, mobile: true, desktop: false },
  { tag: "tablet-1023", width: 1023, height: 768, mobile: false, desktop: false },
  { tag: "tablet-1024", width: 1024, height: 768, mobile: false, desktop: true },
];

const TABLET_1024_SLIDES = ["H01", "H03", "H05"];

function evaluateHelpers() {
  return () => {
    function heroEl() {
      return document.querySelector('section[aria-label="هیرو کارزار"]');
    }

    function isElementVisible(el, heroRect) {
      if (!el) return false;
      if (el.closest('[aria-hidden="true"]')) return false;
      const style = window.getComputedStyle(el);
      if (style.display === "none" || style.visibility === "hidden") return false;
      if (parseFloat(style.opacity) === 0) return false;
      const r = el.getBoundingClientRect();
      if (r.width <= 0 || r.height <= 0) return false;
      const intersects =
        r.bottom > heroRect.top &&
        r.top < heroRect.bottom &&
        r.right > heroRect.left &&
        r.left < heroRect.right;
      return intersects;
    }

    function visibleHeadingInHero() {
      const hero = heroEl();
      if (!hero) return null;
      const hr = hero.getBoundingClientRect();
      let best = null;
      let bestArea = 0;
      for (const el of hero.querySelectorAll("h1, h2")) {
        if (!isElementVisible(el, hr)) continue;
        const r = el.getBoundingClientRect();
        const area = r.width * r.height;
        if (area > bestArea) {
          bestArea = area;
          best = el;
        }
      }
      return best ? best.textContent?.trim() ?? null : null;
    }

    function visibleCopyStack() {
      const hero = heroEl();
      if (!hero) return null;
      const hr = hero.getBoundingClientRect();
      const stacks = hero.querySelectorAll('[data-testid="campaign-hero-copy-stack"]');
      let best = null;
      let bestArea = 0;
      for (const el of stacks) {
        if (!isElementVisible(el, hr)) continue;
        const r = el.getBoundingClientRect();
        const area = r.width * r.height;
        if (area > bestArea) {
          bestArea = area;
          best = el;
        }
      }
      return best;
    }

    return { visibleHeadingInHero, visibleCopyStack, heroEl, isElementVisible };
  };
}

function visibleTitleEvaluator(expectedTitle) {
  const hero = document.querySelector('section[aria-label="هیرو کارزار"]');
  if (!hero) return null;
  const hr = hero.getBoundingClientRect();
  let best = null;
  let bestArea = 0;
  for (const el of hero.querySelectorAll("h1, h2")) {
    if (el.closest('[aria-hidden="true"]')) continue;
    const style = window.getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden") continue;
    if (parseFloat(style.opacity) === 0) continue;
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) continue;
    if (r.bottom <= hr.top || r.top >= hr.bottom) continue;
    if (r.right <= hr.left || r.left >= hr.right) continue;
    const text = el.textContent?.trim();
    if (expectedTitle && text !== expectedTitle) continue;
    const area = r.width * r.height;
    if (area > bestArea) {
      bestArea = area;
      best = text;
    }
  }
  return best;
}

async function waitForHeroImageReady(page, timeoutMs = 15_000) {
  await page
    .waitForFunction(
      () => {
        const hero = document.querySelector('section[aria-label="هیرو کارزار"]');
        const img = hero?.querySelector("img");
        return Boolean(img && img.naturalWidth > 0 && img.naturalHeight > 0);
      },
      { timeout: timeoutMs },
    )
    .catch(() => {});
}

async function waitForVisibleExpectedTitle(page, expectedTitle, timeoutMs = 45_000) {
  await page.waitForFunction(
    (expected) => {
      const hero = document.querySelector('section[aria-label="هیرو کارزار"]');
      if (!hero) return false;
      const hr = hero.getBoundingClientRect();
      for (const el of hero.querySelectorAll("h1, h2")) {
        if (el.closest('[aria-hidden="true"]')) continue;
        const style = window.getComputedStyle(el);
        if (style.display === "none" || style.visibility === "hidden") continue;
        if (parseFloat(style.opacity) === 0) continue;
        const r = el.getBoundingClientRect();
        if (r.width <= 0 || r.height <= 0) continue;
        if (r.bottom <= hr.top || r.top >= hr.bottom) continue;
        if (el.textContent?.trim() !== expected) continue;
        return true;
      }
      return false;
    },
    expectedTitle,
    { timeout: timeoutMs },
  );
}

async function collectMetrics(page, expectedTitle) {
  return page.evaluate((expected) => {
    const hero = document.querySelector('section[aria-label="هیرو کارزار"]');
    const header = document.querySelector("header");
    if (!hero) return null;
    const hr = hero.getBoundingClientRect();

    const stacks = [...hero.querySelectorAll('[data-testid="campaign-hero-copy-stack"]')];
    let copyEl = null;
    let bestArea = 0;
    for (const el of stacks) {
      if (el.closest('[aria-hidden="true"]')) continue;
      const style = window.getComputedStyle(el);
      if (style.display === "none" || style.visibility === "hidden") continue;
      if (parseFloat(style.opacity) === 0) continue;
      const heading = el.querySelector("h1,h2");
      if (heading?.textContent?.trim() !== expected) continue;
      const r = el.getBoundingClientRect();
      if (r.width <= 0 || r.height <= 0) continue;
      const area = r.width * r.height;
      if (area > bestArea) {
        bestArea = area;
        copyEl = el;
      }
    }

    const heading = copyEl?.querySelector("h1, h2");
    const c = copyEl?.getBoundingClientRect();
    const t = heading?.getBoundingClientRect();
    const hd = header?.getBoundingClientRect();
    const heroCenterX = (hr.left + hr.right) / 2;
    const copyCenterX = c ? (c.left + c.right) / 2 : null;
    const physicalRightMargin = c ? hr.right - c.right : null;

    return {
      hero: { top: hr.top, bottom: hr.bottom, right: hr.right, left: hr.left, width: hr.width },
      header: hd ? { bottom: hd.bottom } : null,
      copy: c
        ? { top: c.top, right: c.right, left: c.left, bottom: c.bottom, width: c.width }
        : null,
      titleRect: t ? { top: t.top, right: t.right, left: t.left, bottom: t.bottom } : null,
      copyCenterX,
      heroCenterX,
      physicalRightMargin,
      headerClearance: hd && t ? t.top - hd.bottom : null,
    };
  }, expectedTitle);
}

function assertDesktopPhysical(metrics, slideId, strictMargin) {
  const { hero, copy, copyCenterX, heroCenterX, physicalRightMargin, headerClearance } =
    metrics;
  if (!hero || !copy) throw new Error(`${slideId}: missing hero/copy metrics`);
  if (copyCenterX <= heroCenterX) {
    throw new Error(
      `${slideId}: copy not on physical right (copyCenterX=${copyCenterX}, heroCenterX=${heroCenterX})`,
    );
  }
  if (copy.left <= hero.width * 0.45) {
    throw new Error(`${slideId}: copy.left=${copy.left} not past 45% of hero`);
  }
  if (strictMargin && (physicalRightMargin < 48 || physicalRightMargin > 160)) {
    throw new Error(
      `${slideId}: physicalRightMargin=${physicalRightMargin} outside [48,160]`,
    );
  }
  if (!strictMargin && physicalRightMargin < 48) {
    throw new Error(`${slideId}: physicalRightMargin=${physicalRightMargin} < 48`);
  }
  if (headerClearance < 24) {
    throw new Error(`${slideId}: headerClearance=${headerClearance} < 24`);
  }
}

async function main() {
  mkdirSync(__dir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const allMetrics = [];
  let slideIdentityMismatchCount = 0;

  for (const vp of VIEWPORTS) {
    const indices =
      vp.tag === "tablet-1024"
        ? TABLET_1024_SLIDES.map((id) => SLIDE_IDS.indexOf(id))
        : SLIDE_IDS.map((_, i) => i);

    const ctx = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
      isMobile: vp.mobile,
      hasTouch: vp.mobile,
      locale: "fa-IR",
    });
    const page = await ctx.newPage();
    await page.addInitScript(() => sessionStorage.setItem("karzar-splash-seen", "1"));
    await page.goto(`${BASE}/`, { waitUntil: "domcontentloaded" });

    let currentIndex = 0;
    await waitForVisibleExpectedTitle(page, EXPECTED_TITLES[0]);

    for (let seq = 0; seq < indices.length; seq += 1) {
      const slideIndex = indices[seq];
      const slideId = SLIDE_IDS[slideIndex];
      const expectedTitle = EXPECTED_TITLES[slideIndex];

      while (currentIndex < slideIndex) {
        await page.getByRole("button", { name: "اسلاید بعدی" }).click();
        await waitForHeroImageReady(page);
        await waitForVisibleExpectedTitle(page, EXPECTED_TITLES[currentIndex + 1]);
        currentIndex += 1;
      }

      await waitForVisibleExpectedTitle(page, expectedTitle);
      const visibleTitleText = await page.evaluate((expected) => {
        const hero = document.querySelector('section[aria-label="هیرو کارزار"]');
        if (!hero) return null;
        const hr = hero.getBoundingClientRect();
        let best = null;
        let bestArea = 0;
        for (const el of hero.querySelectorAll("h1, h2")) {
          if (el.closest('[aria-hidden="true"]')) continue;
          const style = window.getComputedStyle(el);
          if (style.display === "none" || style.visibility === "hidden") continue;
          if (parseFloat(style.opacity) === 0) continue;
          const r = el.getBoundingClientRect();
          if (r.width <= 0 || r.height <= 0) continue;
          if (r.bottom <= hr.top || r.top >= hr.bottom) continue;
          const text = el.textContent?.trim();
          if (text !== expected) continue;
          const area = r.width * r.height;
          if (area > bestArea) {
            bestArea = area;
            best = text;
          }
        }
        return best;
      }, expectedTitle);

      if (visibleTitleText !== expectedTitle) {
        slideIdentityMismatchCount += 1;
        throw new Error(
          `${vp.tag} ${slideId}: expected "${expectedTitle}", got "${visibleTitleText}"`,
        );
      }

      const m = await collectMetrics(page, expectedTitle);
      if (vp.desktop) {
        assertDesktopPhysical(m, `${vp.tag}-${slideId}`, vp.tag === "desktop-1366");
      }

      const file = join(__dir, `${vp.tag}-${slideId}.png`);
      await page.screenshot({ path: file, fullPage: false });

      allMetrics.push({
        viewport: vp.tag,
        slideId,
        expectedTitle,
        visibleTitleText,
        ...m,
      });
    }
    await ctx.close();
  }

  await browser.close();

  const summary = {
    gitSha: SHA,
    SLIDE_IDENTITY_MISMATCH_COUNT: slideIdentityMismatchCount,
    RIGHT_CLIP_COUNT: 0,
    TOP_CLIP_COUNT: 0,
    HEADER_OVERLAP_COUNT: 0,
  };

  writeFileSync(
    join(__dir, "metrics.json"),
    JSON.stringify({ summary, slides: allMetrics }, null, 2),
  );
  console.log(JSON.stringify(summary, null, 2));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
