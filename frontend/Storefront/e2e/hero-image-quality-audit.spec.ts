/**
 * Forensic hero capture — requires production server on :3000 (see scripts/hero-quality-browser-audit.mjs).
 * CI uses hero-calibrated-campaign.spec.ts; this spec validates slide identity when HERO_AUDIT_CAPTURE=1.
 */
import { expect, test } from "@playwright/test";

const SLIDES = [
  { id: "H01", title: "تخفیف‌های ویژه‌ی کارزار", desktop: "H01-special-offers-desktop-16x9.webp", mobile: "H01-special-offers-mobile-4x3.webp" },
  { id: "H02", title: "ابزار اندازه‌گیری", desktop: "H02-measuring-tools-desktop-16x9.webp", mobile: "H02-measuring-tools-mobile-4x3.webp" },
  { id: "H03", title: "اینسرت و ابزارهای اینسرتی", desktop: "H03-inserts-turning-tools-desktop-16x9.webp", mobile: "H03-inserts-turning-tools-mobile-4x3.webp" },
  { id: "H04", title: "فرز انگشتی", desktop: "H04-end-mills-desktop-16x9.webp", mobile: "H04-end-mills-mobile-4x3.webp" },
  { id: "H05", title: "دستگاه‌های صنعتی", desktop: "H05-industrial-machines-desktop-16x9.webp", mobile: "H05-industrial-machines-mobile-4x3.webp" },
];

const VIEWPORTS = [
  { width: 390, height: 844, dpr: 3, label: "390x844@3", compact: true },
  { width: 1023, height: 900, dpr: 2, label: "1023x900@2", compact: true },
  { width: 1024, height: 768, dpr: 2, label: "1024x768@2", compact: false },
  { width: 1440, height: 900, dpr: 2, label: "1440x900@2", compact: false },
  { width: 1920, height: 1080, dpr: 2, label: "1920x1080@2", compact: false },
];

const SPLASH_STORAGE_KEY = "karzar-splash-seen";

async function waitSplashDismissed(page: import("@playwright/test").Page) {
  await expect
    .poll(
      async () =>
        page.evaluate((key) => {
          try {
            if (sessionStorage.getItem(key) !== "1") return false;
          } catch {
            return false;
          }
          return (
            document.querySelectorAll(".karzar-splash").length === 0 &&
            document.querySelectorAll("style[data-karzar-splash-boot]").length === 0
          );
        }, SPLASH_STORAGE_KEY),
      { timeout: 35_000 },
    )
    .toBe(true);
}

async function gotoHomeReady(page: import("@playwright/test").Page) {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/", { waitUntil: "domcontentloaded", timeout: 120_000 });
  await expect(page.getByRole("region", { name: "هیرو کارزار" })).toBeVisible({ timeout: 30_000 });
  await waitSplashDismissed(page);
}

async function expectSlide(page: import("@playwright/test").Page, index: number, compact: boolean) {
  const slide = SLIDES[index]!;
  const hero = page.getByRole("region", { name: "هیرو کارزار" });
  await expect(hero.getByRole("heading", { name: slide.title, exact: true })).toBeVisible();
  const expected = compact ? slide.mobile : slide.desktop;
  const img = hero.locator("picture img").first();
  await expect
    .poll(async () => img.evaluate((n) => (n as HTMLImageElement).currentSrc), { timeout: 25_000 })
    .toContain(expected);
  await expect.poll(async () => img.evaluate((n) => {
    const el = n as HTMLImageElement;
    return el.complete && el.naturalWidth > 0;
  }), { timeout: 25_000 }).toBe(true);
}

test.describe("hero image quality audit", () => {
  test.skip(!process.env.HERO_AUDIT_CAPTURE, "set HERO_AUDIT_CAPTURE=1 with next start on :3000");

  for (const vp of VIEWPORTS) {
    test(`mandatory matrix ${vp.label}`, async ({ browser }) => {
      test.setTimeout(300_000);
      const context = await browser.newContext({
        viewport: { width: vp.width, height: vp.height },
        deviceScaleFactor: vp.dpr,
      });
      const page = await context.newPage();
      await gotoHomeReady(page);
      for (let index = 0; index < SLIDES.length; index += 1) {
        await expectSlide(page, index, vp.compact);
        if (index < SLIDES.length - 1) {
          const hero = page.getByRole("region", { name: "هیرو کارزار" });
          const before = await hero.locator("picture img").first().evaluate((n) => (n as HTMLImageElement).currentSrc);
          await hero.focus();
          await page.keyboard.press("ArrowLeft");
          await expect
            .poll(async () => hero.locator("picture img").first().evaluate((n) => (n as HTMLImageElement).currentSrc), {
              timeout: 20_000,
            })
            .not.toBe(before);
          await expectSlide(page, index + 1, vp.compact);
        }
      }
      await context.close();
    });
  }
});
