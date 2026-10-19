import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const tag = process.argv[2] ?? "run";
const outRoot =
  process.argv[3] ??
  join(process.cwd(), "../../audit/hero-image-quality-20261019/browser-capture", tag);
mkdirSync(outRoot, { recursive: true });

const VIEWPORTS = [
  { w: 390, h: 844, dpr: 3, label: "390x844@3" },
  { w: 1023, h: 900, dpr: 2, label: "1023x900@2" },
  { w: 1024, h: 768, dpr: 2, label: "1024x768@2" },
  { w: 1440, h: 900, dpr: 2, label: "1440x900@2" },
  { w: 1920, h: 1080, dpr: 2, label: "1920x1080@2" },
];

async function captureInitialLoad(page) {
  const heroUrls = [];
  page.on("request", (req) => {
    const u = req.url();
    if (u.includes("calibrated-20261018") || u.includes("/_next/image")) heroUrls.push(u);
  });
  await page.goto("http://127.0.0.1:3000/", { waitUntil: "domcontentloaded" });
  await page.waitForSelector('[data-testid="campaign-hero-fullbleed"], [data-testid="campaign-hero-compact"]', {
    timeout: 60_000,
  });
  await page.waitForFunction(() => {
    const img = document.querySelector(
      '[data-testid="campaign-hero-fullbleed"] img, [data-testid="campaign-hero-compact-media"] img',
    );
    return img && img.complete && img.naturalWidth > 0;
  });
  const lcp = await page.evaluate(() => {
    return new Promise((resolve) => {
      let value = null;
      try {
        new PerformanceObserver((list) => {
          const entries = list.getEntries();
          const last = entries[entries.length - 1];
          if (last) value = { startTime: last.startTime, size: last.size, url: last.url };
        }).observe({ type: "largest-contentful-paint", buffered: true });
      } catch {
        resolve(null);
        return;
      }
      setTimeout(() => resolve(value), 500);
    });
  });
  await page.waitForTimeout(800);
  const calibrated = [...new Set(heroUrls.filter((u) => u.includes("calibrated-20261018")))];
  const optimized = [...new Set(heroUrls.filter((u) => u.includes("/_next/image")))];
  return {
    heroRequestCount: heroUrls.length,
    uniqueCalibratedUrls: calibrated,
    uniqueOptimizedUrls: optimized,
    lcp,
  };
}

const browser = await chromium.launch({ channel: "chrome", headless: true });
let initialLoad = null;

for (const vp of VIEWPORTS) {
  const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h }, deviceScaleFactor: vp.dpr });
  const page = await ctx.newPage();
  if (vp.label === "1920x1080@2") initialLoad = await captureInitialLoad(page);
  for (let i = 0; i < 5; i++) {
    await page.goto("http://127.0.0.1:3000/", { waitUntil: "domcontentloaded" });
    await page.waitForSelector('[data-testid="campaign-hero-fullbleed"], [data-testid="campaign-hero-compact"]');
    await page
      .waitForFunction(() => {
        const img = document.querySelector(
          '[data-testid="campaign-hero-fullbleed"] img, [data-testid="campaign-hero-compact-media"] img',
        );
        return img && img.complete && img.naturalWidth > 0;
      })
      .catch(() => {});
    if (i > 0) {
      const prevSrc = await page.evaluate(
        () =>
          document.querySelector(
            '[data-testid="campaign-hero-fullbleed"] img, [data-testid="campaign-hero-compact-media"] img',
          )?.currentSrc ?? "",
      );
      await page.getByRole("button", { name: "اسلاید بعدی" }).click();
      await page
        .waitForFunction(
          (p) => {
            const img = document.querySelector(
              '[data-testid="campaign-hero-fullbleed"] img, [data-testid="campaign-hero-compact-media"] img',
            );
            return img && img.currentSrc && img.currentSrc !== p && img.naturalWidth > 0;
          },
          prevSrc,
          { timeout: 12_000 },
        )
        .catch(() => page.waitForTimeout(800));
    }
    const metrics = await page.evaluate(() => {
      const compact = !!document.querySelector('[data-testid="campaign-hero-compact"]');
      const img = document.querySelector(
        '[data-testid="campaign-hero-fullbleed"] img, [data-testid="campaign-hero-compact-media"] img',
      );
      if (!img) return null;
      const cs = getComputedStyle(img);
      const rect = img.getBoundingClientRect();
      const picture = img.closest("picture");
      const mobileSource = picture?.querySelector("source");
      return {
        compact,
        currentSrc: img.currentSrc,
        naturalWidth: img.naturalWidth,
        naturalHeight: img.naturalHeight,
        clientWidth: Math.round(rect.width),
        clientHeight: Math.round(rect.height),
        dpr: window.devicePixelRatio,
        objectFit: cs.objectFit,
        objectPosition: cs.objectPosition,
        mobileMedia: mobileSource?.getAttribute("media") ?? null,
        loading: img.loading,
        fetchPriority: img.fetchPriority,
      };
    });
    const hero = `H0${i + 1}`;
    await page.screenshot({ path: join(outRoot, `${vp.label}_${hero}.png`) });
    writeFileSync(join(outRoot, `${vp.label}_${hero}.json`), JSON.stringify(metrics, null, 2));
  }
  await ctx.close();
}

writeFileSync(join(outRoot, "initial-load-1920.json"), JSON.stringify(initialLoad, null, 2));
await browser.close();
console.log("wrote", outRoot);
