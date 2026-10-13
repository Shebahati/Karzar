/**
 * Read-only live homepage hero probe (production).
 *   node audit/hero-reborn-5-live-repair-2026-10-13/live-probe.mjs
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
const BASE = "https://www.karzartools.com";
const VIEWPORTS = [
  { id: "1920x1080", w: 1920, h: 1080 },
  { id: "390x844", w: 390, h: 844 },
];

async function main() {
  const browser = await chromium.launch();
  const manifest = { capturedAt: new Date().toISOString(), base: BASE, viewports: [], heroPack: null };
  const page0 = await (await browser.newContext()).newPage();
  const packRes = await page0.goto(`${BASE}/hero-design.json`, { waitUntil: "domcontentloaded" });
  manifest.heroPack = {
    status: packRes?.status(),
    body: JSON.parse(await page0.textContent("pre, body") || await page0.evaluate(() => document.body.innerText)),
  };
  await page0.close();

  for (const vp of VIEWPORTS) {
    const ctx = await browser.newContext({
      viewport: { width: vp.w, height: vp.h },
      reducedMotion: "no-preference",
    });
    const page = await ctx.newPage();
    const errors = [];
    page.on("console", (m) => {
      if (m.type() === "error") errors.push(m.text());
    });
    const failed = [];
    page.on("response", (r) => {
      const u = r.url();
      if ((u.includes("/images/hero/") || u.includes("/_next/image")) && r.status() >= 400) {
        failed.push({ url: u, status: r.status() });
      }
    });
    await page.goto(`${BASE}/`, { waitUntil: "domcontentloaded", timeout: 120_000 });
    await page.waitForTimeout(2500);
    const layout = await page.evaluate(() => {
      const hero = document.querySelector('section[aria-label="هیرو کارزار"]');
      const outer = hero?.parentElement;
      const next = outer?.nextElementSibling;
      const hr = hero?.getBoundingClientRect();
      const or = outer?.getBoundingClientRect();
      const nr = next?.getBoundingClientRect();
      const gap = hr && nr ? nr.top - hr.bottom : null;
      return {
        hero: hr ? { h: hr.height, bottom: hr.bottom } : null,
        outer: or ? { h: or.height, bottom: or.bottom } : null,
        nextTop: nr?.top ?? null,
        gap,
        overlap: gap !== null && gap < -2,
      };
    });
    await mkdir(path.join(OUT, "screenshots"), { recursive: true });
    await page.screenshot({ path: path.join(OUT, "screenshots", `${vp.id}-fold.png`) });
    manifest.viewports.push({ id: vp.id, layout, errors, failedRequests: failed });
    await ctx.close();
  }
  await writeFile(path.join(OUT, "manifest.json"), JSON.stringify(manifest, null, 2));
  await browser.close();
  console.log("Wrote", path.join(OUT, "manifest.json"));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
