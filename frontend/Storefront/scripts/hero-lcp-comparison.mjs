import { chromium } from "playwright";
import { writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import {
  assertHeroNotObscured,
  gotoHomeReady,
  installPerfInstrumentation,
  median,
  waitSplashDismissed,
} from "./hero-audit-lib.mjs";

const outDir = join(process.cwd(), "../../audit/hero-image-quality-20261019/lcp-comparison");
mkdirSync(outDir, { recursive: true });
const RUNS = 5;

async function oneRun(page) {
  const heroResponses = [];
  page.on("response", (res) => {
    const u = res.url();
    if (u.includes("photo-20261021-v2") || u.includes("/_next/image")) {
      heroResponses.push({ url: u, status: res.status() });
    }
  });
  await gotoHomeReady(page);
  await page.waitForFunction(() => {
    const img = document.querySelector(
      '[data-testid="campaign-hero-fullbleed"] picture img, [data-testid="campaign-hero-compact-media"] picture img',
    );
    return img && img.complete && img.naturalWidth > 0;
  });
  await assertHeroNotObscured(page);
  const perf = await page.evaluate(() => {
    const bag = window.__karzarPerf || { lcp: [], navigationStart: 0 };
    const lcpEntries = bag.lcp;
    const last = lcpEntries.length ? lcpEntries[lcpEntries.length - 1] : null;
    const img = document.querySelector(
      '[data-testid="campaign-hero-fullbleed"] picture img, [data-testid="campaign-hero-compact-media"] picture img',
    );
    let lcpTransferSize = null;
    const lcpUrl = last?.url || last?.src || "";
    if (lcpUrl) {
      const res = performance.getEntriesByType("resource").find((r) => r.name === lcpUrl);
      if (res) lcpTransferSize = res.transferSize ?? null;
    }
    const heroIsLcp =
      !!last &&
      !!img &&
      (last.url === img.currentSrc ||
        last.src === img.currentSrc ||
        (last.tagName === "IMG" &&
          img ===
            document.querySelector(
              '[data-testid="campaign-hero-fullbleed"] picture img, [data-testid="campaign-hero-compact-media"] picture img',
            )));
    const imageRequestCount = performance
      .getEntriesByType("resource")
      .filter((r) => r.initiatorType === "img" || r.name.includes("photo-20261021-v2") || r.name.includes("/_next/image"))
      .length;
    return {
      lcpEntries,
      lcpLast: last,
      lcpRelativeMs: last?.startTime ?? null,
      lcpElement: last
        ? {
            tagName: last.tagName,
            testId: last.testId,
            url: last.url,
            src: last.src,
            size: last.size,
          }
        : null,
      heroImgSrc: img?.currentSrc ?? "",
      heroNaturalWidth: img?.naturalWidth ?? 0,
      dpr: window.devicePixelRatio,
      lcpIsHeroImage: Boolean(heroIsLcp),
      lcpTransferSize,
      imageRequestCount,
      navigationStart: bag.navigationStart,
    };
  });
  return { heroResponses, ...perf };
}

const label = process.argv[2] || "after-fix";
const results = [];
const browser = await chromium.launch({ channel: "chrome", headless: true });
for (let i = 0; i < RUNS; i += 1) {
  const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  await installPerfInstrumentation(page);
  results.push(await oneRun(page));
  await ctx.close();
}
await browser.close();

const lcpTimes = results.map((r) => r.lcpRelativeMs).filter((v) => typeof v === "number");
const heroReqCounts = results.map((r) => r.heroResponses.length);
const lcpIsHero = results.map((r) => r.lcpIsHeroImage);
const summary = {
  label,
  runs: RUNS,
  dpr: 2,
  viewport: "1920x1080@2",
  cache: "fresh browser context per run (no HTTP cache reuse across runs)",
  medianLcpMs: lcpTimes.length ? median(lcpTimes) : null,
  lcpMsPerRun: lcpTimes,
  lcpMsMin: lcpTimes.length ? Math.min(...lcpTimes) : null,
  lcpMsMax: lcpTimes.length ? Math.max(...lcpTimes) : null,
  medianHeroRequestCount: heroReqCounts.length ? median(heroReqCounts) : null,
  heroRequestCounts: heroReqCounts,
  lcpIsHeroImagePerRun: lcpIsHero,
  runsDetail: results,
};
writeFileSync(join(outDir, `${label}.json`), JSON.stringify(summary, null, 2));
console.log(JSON.stringify(summary, null, 2));
