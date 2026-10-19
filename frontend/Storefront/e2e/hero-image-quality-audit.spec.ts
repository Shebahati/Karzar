/**
 * Forensic hero image delivery audit — production build only.
 */
import { test, expect } from "@playwright/test";
import { writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";

const OUT = join(process.cwd(), "../../audit/hero-image-quality-20261019/browser-capture");
const VIEWPORTS: { w: number; h: number; dpr: number; label: string }[] = [
  { w: 320, h: 720, dpr: 2, label: "320x720@2" },
  { w: 390, h: 844, dpr: 2, label: "390x844@2" },
  { w: 390, h: 844, dpr: 3, label: "390x844@3" },
  { w: 430, h: 932, dpr: 3, label: "430x932@3" },
  { w: 768, h: 1024, dpr: 2, label: "768x1024@2" },
  { w: 1023, h: 900, dpr: 1, label: "1023x900@1" },
  { w: 1023, h: 900, dpr: 2, label: "1023x900@2" },
  { w: 1024, h: 768, dpr: 1, label: "1024x768@1" },
  { w: 1024, h: 768, dpr: 2, label: "1024x768@2" },
  { w: 1366, h: 768, dpr: 1, label: "1366x768@1" },
  { w: 1366, h: 768, dpr: 2, label: "1366x768@2" },
  { w: 1440, h: 900, dpr: 1, label: "1440x900@1" },
  { w: 1440, h: 900, dpr: 2, label: "1440x900@2" },
  { w: 1920, h: 1080, dpr: 1, label: "1920x1080@1" },
  { w: 1920, h: 1080, dpr: 2, label: "1920x1080@2" },
  { w: 2560, h: 1440, dpr: 2, label: "2560x1440@2" },
];
const HERO_LABELS = ["H01", "H02", "H03", "H04", "H05"];

async function waitForHeroImage(page: import("@playwright/test").Page) {
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await page.waitForSelector('[data-testid="campaign-hero-fullbleed"], [data-testid="campaign-hero-compact"]', { timeout: 30_000 });
  await page.waitForFunction(() => {
    const img = document.querySelector<HTMLImageElement>(
      '[data-testid="campaign-hero-fullbleed"] img, [data-testid="campaign-hero-compact-media"] img',
    );
    return img && img.complete && img.naturalWidth > 0;
  });
}

test.describe("hero image quality audit", () => {
  test("capture delivery matrix and screenshots", async ({ page, browser }) => {
    test.setTimeout(600_000);
    const tag = process.env.HERO_AUDIT_TAG ?? "run";
    const outDir = join(OUT, tag);
    mkdirSync(outDir, { recursive: true });
    const rows: Record<string, string | number | boolean | null>[] = [];

    for (const vp of VIEWPORTS) {
      const context = await browser.newContext({
        viewport: { width: vp.w, height: vp.h },
        deviceScaleFactor: vp.dpr,
      });
      const p = await context.newPage();
      for (let heroIndex = 0; heroIndex < 5; heroIndex++) {
        await waitForHeroImage(p);
        if (heroIndex > 0) {
          const next = p.locator('[aria-label="اسلاید بعدی"]').first();
          if (await next.isVisible().catch(() => false)) {
            await next.click();
            await p.waitForTimeout(500);
          }
        }
        const metrics = await p.evaluate(() => {
          const compact = !!document.querySelector('[data-testid="campaign-hero-compact"]');
          const img = document.querySelector<HTMLImageElement>(
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
            clientWidth: rect.width,
            clientHeight: rect.height,
            objectFit: cs.objectFit,
            objectPosition: cs.objectPosition,
            mobileMedia: mobileSource?.getAttribute("media") ?? null,
            dpr: window.devicePixelRatio,
          };
        });
        expect(metrics).not.toBeNull();
        const m = metrics!;
        const hero = HERO_LABELS[heroIndex];
        await p.screenshot({ path: join(outDir, `${vp.label}_${hero}.png`) });
        rows.push({
          viewport: vp.label,
          hero,
          compact: m.compact,
          devicePixelRatio: m.dpr,
          currentSrc: m.currentSrc,
          naturalWidth: m.naturalWidth,
          naturalHeight: m.naturalHeight,
          elementWidth: Math.round(m.clientWidth),
          elementHeight: Math.round(m.clientHeight),
          physicalPxDemandWidth: Math.round(m.clientWidth * m.dpr),
          objectFit: m.objectFit,
          objectPosition: m.objectPosition,
          usesNextOptimizer: m.currentSrc.includes("/_next/image"),
          directCalibratedWebp: m.currentSrc.includes("/calibrated-20261018/"),
          mobileMediaQuery: m.mobileMedia,
        });
      }
      await context.close();
    }
    writeFileSync(join(outDir, "delivery-matrix.json"), JSON.stringify(rows, null, 2));
  });
});
