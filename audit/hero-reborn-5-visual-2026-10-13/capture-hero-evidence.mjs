/**
 * One-off visual evidence capture for Heroes Reborn 5 (PR #481).
 * Run from frontend/Storefront:
 *   node ../../audit/hero-reborn-5-visual-2026-10-13/capture-hero-evidence.mjs
 *
 * Requires dev server on :3000 or set BASE_URL.
 */
import { createRequire } from "node:module";
import { mkdir, rename, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(
  path.join(path.dirname(fileURLToPath(import.meta.url)), "../../frontend/Storefront/package.json"),
);
const { chromium } = require("@playwright/test");

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT = __dirname;
const BASE_URL = process.env.BASE_URL ?? "http://127.0.0.1:3000";

const VIEWPORTS = [
  { id: "1920x1080", width: 1920, height: 1080 },
  { id: "1440x900", width: 1440, height: 900 },
  { id: "1366x768", width: 1366, height: 768 },
  { id: "768x1024", width: 768, height: 1024 },
  { id: "390x844", width: 390, height: 844 },
];

const SLIDE_TITLES = [
  "تخفیف‌های ویژه‌ی کارزار",
  "ابزار اندازه‌گیری",
  "اینسرت و ابزارهای اینسرتی",
  "فرز انگشتی",
  "دستگاه‌های صنعتی",
];

const SLUGS = ["h01-discounts", "h02-metrology", "h03-inserts", "h04-endmills", "h05-machines"];

async function waitHeroSettled(page) {
  await page.waitForSelector('section[aria-label="هیرو کارزار"]', { timeout: 60_000 });
  await page.waitForTimeout(1200);
}

async function visibleHeroTitle(page) {
  const hero = page.locator('section[aria-label="هیرو کارزار"]');
  const h = hero.locator("h1, h2").first();
  const text = (await h.textContent())?.trim() ?? "";
  return SLIDE_TITLES.find((t) => t === text) ?? text;
}

async function clickNext(page, mobile) {
  const hero = page.locator('section[aria-label="هیرو کارزار"]');
  if (mobile) {
    await hero.getByRole("button", { name: "اسلاید بعدی" }).click({ force: true });
  } else {
    await hero.hover({ position: { x: 10, y: 200 } });
    await hero.getByRole("button", { name: "اسلاید بعدی" }).click({ force: true });
  }
  await page.waitForTimeout(900);
}

async function clickPrev(page, mobile) {
  const hero = page.locator('section[aria-label="هیرو کارزار"]');
  if (mobile) {
    await hero.getByRole("button", { name: "اسلاید قبلی" }).click({ force: true });
  } else {
    await hero.hover({ position: { x: 10, y: 200 } });
    await hero.getByRole("button", { name: "اسلاید قبلی" }).click({ force: true });
  }
  await page.waitForTimeout(900);
}

async function captureLayoutMetrics(page) {
  return await page.evaluate(() => {
    const hero = document.querySelector('section[aria-label="هیرو کارزار"]');
    if (!hero) return null;
    const hr = hero.getBoundingClientRect();
    const title = hero.querySelector("h1, h2");
    const tr = title?.getBoundingClientRect();
    const subtitle = hero.querySelector("h1 ~ p, h2 ~ p");
    const sr = subtitle?.getBoundingClientRect();
    const orbs = hero.querySelectorAll('[class*="orb"] button, nav button');
    const orbRects = Array.from(orbs)
      .slice(0, 6)
      .map((el) => {
        const r = el.getBoundingClientRect();
        return { x: r.x, y: r.y, w: r.width, h: r.height };
      });
    const titleOverlapsOrb =
      tr && orbRects.length
        ? orbRects.some(
            (o) =>
              tr.right > o.x &&
              tr.left < o.x + o.w &&
              tr.bottom > o.y &&
              tr.top < o.y + o.h,
          )
        : false;
    return {
      hero: { x: hr.x, y: hr.y, w: hr.width, h: hr.height },
      title: tr
        ? { x: tr.x, y: tr.y, w: tr.width, h: tr.height, text: title?.textContent?.trim() }
        : null,
      subtitle: sr
        ? { x: sr.x, y: sr.y, w: sr.width, h: sr.height, text: subtitle?.textContent?.trim() }
        : null,
      titleOverlapsOrb,
      viewport: { w: window.innerWidth, h: window.innerHeight },
    };
  });
}

async function main() {
  await mkdir(path.join(OUT, "screenshots"), { recursive: true });
  await mkdir(path.join(OUT, "videos"), { recursive: true });

  const browser = await chromium.launch();
  const manifest = {
    capturedAt: new Date().toISOString(),
    baseUrl: BASE_URL,
    reducedMotion: true,
    viewports: [],
    transitions: [],
    slideTitleChecks: [],
  };

  for (const vp of VIEWPORTS) {
    const mobile = vp.width < 768;
    const ctx = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
      locale: "fa-IR",
      reducedMotion: "reduce",
    });
    const page = await ctx.newPage();
    await page.goto(BASE_URL, { waitUntil: "domcontentloaded", timeout: 120_000 });
    await waitHeroSettled(page);

    const vpEntry = { id: vp.id, shots: [] };
    for (let i = 0; i < 5; i++) {
      if (i > 0) await clickNext(page, mobile);
      const expected = SLIDE_TITLES[i];
      let title = await visibleHeroTitle(page);
      if (title !== expected) {
        await page.waitForTimeout(500);
        title = await visibleHeroTitle(page);
      }
      const file = path.join(OUT, "screenshots", `${vp.id}__${SLUGS[i]}.png`);
      await page.screenshot({ path: file, fullPage: false });
      const metrics = await captureLayoutMetrics(page);
      vpEntry.shots.push({
        slide: i + 1,
        slug: SLUGS[i],
        expectedTitle: expected,
        observedTitle: title,
        titleMatch: title === expected,
        metrics,
      });
    }
    manifest.viewports.push(vpEntry);
    await ctx.close();
  }

  const deskCtx = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    locale: "fa-IR",
    reducedMotion: "reduce",
    recordVideo: { dir: path.join(OUT, "videos"), size: { width: 1920, height: 1080 } },
  });
  const deskPage = await deskCtx.newPage();
  await deskPage.goto(BASE_URL, { waitUntil: "domcontentloaded", timeout: 120_000 });
  await waitHeroSettled(deskPage);
  const deskTitles = [];
  for (let i = 0; i < 5; i++) {
    deskTitles.push(await visibleHeroTitle(deskPage));
    if (i < 4) await clickNext(deskPage, false);
    await deskPage.waitForTimeout(500);
  }
  for (let i = 0; i < 4; i++) {
    await clickPrev(deskPage, false);
    await deskPage.waitForTimeout(500);
  }
  deskTitles.push(await visibleHeroTitle(deskPage));
  const deskVideoPath = await deskPage.video()?.path();
  await deskCtx.close();
  if (deskVideoPath) {
    await rename(deskVideoPath, path.join(OUT, "videos", "desktop-1920x1080-forward-back.webm"));
  }
  manifest.transitions.push({
    kind: "desktop-1920x1080",
    forwardTitles: deskTitles.slice(0, 5),
    afterBackward: deskTitles[5] ?? null,
    videoFile: "desktop-1920x1080-forward-back.webm",
  });

  const mobCtx = await browser.newContext({
    viewport: { width: 390, height: 844 },
    locale: "fa-IR",
    reducedMotion: "reduce",
    recordVideo: { dir: path.join(OUT, "videos"), size: { width: 390, height: 844 } },
  });
  const mobPage = await mobCtx.newPage();
  await mobPage.goto(BASE_URL, { waitUntil: "domcontentloaded", timeout: 120_000 });
  await waitHeroSettled(mobPage);
  const mobTitles = [];
  for (let i = 0; i < 5; i++) {
    mobTitles.push(await visibleHeroTitle(mobPage));
    if (i < 4) await clickNext(mobPage, true);
    await mobPage.waitForTimeout(500);
  }
  for (let i = 0; i < 4; i++) {
    await clickPrev(mobPage, true);
    await mobPage.waitForTimeout(500);
  }
  mobTitles.push(await visibleHeroTitle(mobPage));
  const mobVideoPath = await mobPage.video()?.path();
  await mobCtx.close();
  if (mobVideoPath) {
    await rename(mobVideoPath, path.join(OUT, "videos", "mobile-390x844-forward-back.webm"));
  }
  manifest.transitions.push({
    kind: "mobile-390x844",
    forwardTitles: mobTitles.slice(0, 5),
    afterBackward: mobTitles[5] ?? null,
    videoFile: "mobile-390x844-forward-back.webm",
  });

  manifest.slideTitleChecks = manifest.viewports.flatMap((v) =>
    v.shots.map((s) => ({
      viewport: v.id,
      slide: s.slide,
      titleMatch: s.titleMatch,
      expected: s.expectedTitle,
      observed: s.observedTitle,
      titleOverlapsOrb: s.metrics?.titleOverlapsOrb ?? null,
    })),
  );

  const allTitleMatch = manifest.slideTitleChecks.every((c) => c.titleMatch);
  manifest.summary = {
    screenshotCount: manifest.slideTitleChecks.length,
    allTitlesMatch: allTitleMatch,
    layoutOverlapFlags: manifest.slideTitleChecks.filter((c) => c.titleOverlapsOrb).length,
  };

  await writeFile(path.join(OUT, "manifest.json"), JSON.stringify(manifest, null, 2), "utf8");
  await browser.close();
  console.log("Wrote evidence to", OUT);
  if (!allTitleMatch) process.exit(1);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
