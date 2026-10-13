/**
 * Post-fix local production-build hero probe.
 *   cd frontend/Storefront && npm run build && npm run start -- -p 3010
 *   node audit/hero-reborn-5-live-repair-2026-10-13/post-fix-probe.mjs
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

async function measureLayout(page) {
  return page.evaluate(() => {
    const hero = document.querySelector('section[aria-label="هیرو کارزار"]');
    const outer = hero?.parentElement;
    const next = outer?.nextElementSibling;
    const hr = hero?.getBoundingClientRect();
    const or = outer?.getBoundingClientRect();
    const nr = next?.getBoundingClientRect();
    const gap = hr && nr ? nr.top - hr.bottom : null;
    return {
      heroTop: hr?.top ?? null,
      heroBottom: hr?.bottom ?? null,
      nextTop: nr?.top ?? null,
      gap,
      outerH: or?.height ?? null,
      heroH: hr?.height ?? null,
      overlap: gap !== null && gap < -2,
    };
  });
}

async function main() {
  const browser = await chromium.launch();
  const manifest = {
    kind: "post-fix-local-prod",
    capturedAt: new Date().toISOString(),
    base: BASE,
    viewports: [],
    transitions: [],
  };

  for (const vp of VIEWPORTS) {
    const ctx = await browser.newContext({
      viewport: { width: vp.w, height: vp.h },
      reducedMotion: "no-preference",
    });
    const page = await ctx.newPage();
    await page.goto(`${BASE}/`, { waitUntil: "networkidle", timeout: 120_000 });
    await page.waitForTimeout(1500);
    const layout = await measureLayout(page);
    await mkdir(path.join(OUT, "screenshots", "post-fix"), { recursive: true });
    await page.screenshot({
      path: path.join(OUT, "screenshots", "post-fix", `${vp.id}-fold.png`),
    });
    manifest.viewports.push({ id: vp.id, layout });
    await ctx.close();
  }

  const ctx = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    reducedMotion: "no-preference",
  });
  const page = await ctx.newPage();
  await page.goto(`${BASE}/`, { waitUntil: "networkidle", timeout: 120_000 });
  await page.waitForTimeout(2000);

  const slides = ["H01", "H02", "H03", "H04", "H05", "H01"];
  for (let i = 0; i < slides.length - 1; i++) {
    const before = await page.evaluate(() => ({
      title: document.querySelector("section[aria-label='هیرو کارزار'] h1")?.textContent?.trim(),
      img: document.querySelector("section[aria-label='هیرو کارزار'] img")?.getAttribute("src") ?? "",
      dock: document.querySelector('nav[aria-label="دسته‌های پاور هیرو"]')?.textContent ?? "",
    }));
    await page.getByRole("button", { name: "اسلاید بعدی" }).click();
    await page.waitForTimeout(2500);
    const after = await page.evaluate(() => ({
      title: document.querySelector("section[aria-label='هیرو کارزار'] h1")?.textContent?.trim(),
      img: document.querySelector("section[aria-label='هیرو کارزار'] img")?.getAttribute("src") ?? "",
      dock: document.querySelector('nav[aria-label="دسته‌های پاور هیرو"]')?.textContent ?? "",
    }));
    manifest.transitions.push({ step: `${slides[i]}→${slides[i + 1]}`, before, after });
  }
  await ctx.close();

  await writeFile(path.join(OUT, "post-fix-manifest.json"), JSON.stringify(manifest, null, 2));
  await browser.close();
  console.log("Wrote", path.join(OUT, "post-fix-manifest.json"));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
