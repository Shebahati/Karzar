import { expect, test, type Page } from "@playwright/test";

const SLIDES = [
  {
    title: "تخفیف‌های ویژه‌ی کارزار",
    desktop: "H01-special-offers-desktop-16x9.webp",
    mobile: "H01-special-offers-mobile-4x3.webp",
    cta: "مشاهده تخفیف‌ها",
  },
  {
    title: "ابزار اندازه‌گیری",
    desktop: "H02-measuring-tools-desktop-16x9.webp",
    mobile: "H02-measuring-tools-mobile-4x3.webp",
    cta: "مشاهده ابزار اندازه‌گیری",
  },
  {
    title: "اینسرت و ابزارهای اینسرتی",
    desktop: "H03-inserts-turning-tools-desktop-16x9.webp",
    mobile: "H03-inserts-turning-tools-mobile-4x3.webp",
    cta: "مشاهده اینسرت‌ها",
    secondary: "مشاهده ابزارهای اینسرتی",
  },
  {
    title: "فرز انگشتی",
    desktop: "H04-end-mills-desktop-16x9.webp",
    mobile: "H04-end-mills-mobile-4x3.webp",
    cta: "مشاهده فرزهای انگشتی",
  },
  {
    title: "دستگاه‌های صنعتی",
    desktop: "H05-industrial-machines-desktop-16x9.webp",
    mobile: "H05-industrial-machines-mobile-4x3.webp",
    cta: "مشاهده دستگاه‌های صنعتی",
  },
] as const;

const REVIEW_VIEWPORTS = [
  { width: 390, height: 844, name: "390x844" },
  { width: 768, height: 1024, name: "768x1024" },
  { width: 1440, height: 900, name: "1440x900" },
] as const;

function shotPath(viewport: string, slide: string) {
  return `test-results/hero-review/${viewport}-${slide}.png`;
}

async function gotoHome(page: Page) {
  await page.goto("/", { waitUntil: "domcontentloaded", timeout: 120_000 });
  await expect(page.getByRole("region", { name: "هیرو کارزار" })).toBeVisible({
    timeout: 30_000,
  });
}

async function activeHero(page: Page) {
  const compact = page.locator('[data-testid="campaign-hero-compact"]:visible');
  if ((await compact.count()) > 0) return compact.first();
  return page.locator('[data-testid="campaign-hero-fullbleed"]:visible').first();
}

async function expectSlide(page: Page, index: number, compact: boolean) {
  const slide = SLIDES[index]!;
  const hero = await activeHero(page);
  await expect(hero.getByRole("heading", { name: slide.title })).toBeVisible();
  await expect(hero.getByRole("link", { name: slide.cta })).toBeVisible();
  if ("secondary" in slide && slide.secondary) {
    const secondary = hero.getByRole("link", { name: slide.secondary });
    await expect(secondary).toBeVisible();
    const box = await secondary.boundingBox();
    expect(box?.width ?? 0).toBeGreaterThanOrEqual(44);
    expect(box?.height ?? 0).toBeGreaterThanOrEqual(44);
  }

  const img = hero.locator("picture img").first();
  await expect(img).toBeVisible();
  await expect
    .poll(async () => img.evaluate((node) => (node as HTMLImageElement).currentSrc), {
      timeout: 20_000,
    })
    .toContain(compact ? slide.mobile : slide.desktop);
  const currentSrc = await img.evaluate((node) => (node as HTMLImageElement).currentSrc);
  if (compact) {
    expect(currentSrc).not.toContain("desktop-16x9");
    expect(currentSrc).not.toContain("w=3840");
  }
  const failed = currentSrc.includes("w=3840") || currentSrc.includes("w=2880");
  expect(failed).toBe(false);

  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(1);
}

test.describe("calibrated five-hero campaign", () => {
  test.beforeEach(async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
  });

  for (const viewport of REVIEW_VIEWPORTS) {
    test(`renders all five slides at ${viewport.name}`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await gotoHome(page);
      const compact = viewport.width <= 1023;
      if (compact) {
        await expect(page.getByTestId("campaign-hero-compact").first()).toBeVisible();
      } else {
        await expect(page.getByTestId("campaign-hero-fullbleed").first()).toBeVisible();
      }

      for (let index = 0; index < SLIDES.length; index += 1) {
        await expectSlide(page, index, compact);
        const hero = page.getByRole("region", { name: "هیرو کارزار" });
        await hero.screenshot({
          path: shotPath(viewport.name, `H0${index + 1}`),
        });
        if (index < SLIDES.length - 1) {
          const region = page.getByRole("region", { name: "هیرو کارزار" });
          await region.focus();
          await page.keyboard.press("ArrowLeft");
        }
      }
    });
  }

  test("switches art direction at the 1023/1024 boundary", async ({ page }) => {
    await page.setViewportSize({ width: 1023, height: 900 });
    await gotoHome(page);
    await expect(page.getByTestId("campaign-hero-compact").first()).toBeVisible();
    const compactSource = page.locator("picture source").first();
    await expect(compactSource).toHaveAttribute("media", "(max-width: 1023px)");
    await expectSlide(page, 0, true);
    await page
      .getByRole("region", { name: "هیرو کارزار" })
      .screenshot({ path: shotPath("1023x900", "H01") });

    await page.setViewportSize({ width: 1024, height: 768 });
    await expect(page.getByTestId("campaign-hero-fullbleed").first()).toBeVisible();
    await expectSlide(page, 0, false);
    await page
      .getByRole("region", { name: "هیرو کارزار" })
      .screenshot({ path: shotPath("1024x768", "H01") });
  });

  test("covers the remaining representative widths without overflow", async ({ page }) => {
    const widths = [
      { width: 360, height: 800, compact: true },
      { width: 430, height: 932, compact: true },
      { width: 1280, height: 800, compact: false },
      { width: 1366, height: 768, compact: false },
      { width: 1920, height: 1080, compact: false },
    ];
    await page.setViewportSize({ width: widths[0]!.width, height: widths[0]!.height });
    await gotoHome(page);
    for (const viewport of widths) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      if (viewport.compact) {
        await expect(page.getByTestId("campaign-hero-compact").first()).toBeVisible();
      } else {
        await expect(page.getByTestId("campaign-hero-fullbleed").first()).toBeVisible();
      }
      await expectSlide(page, 0, viewport.compact);
    }
  });

  test("keeps H03 controls usable at 320px", async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 720 });
    await gotoHome(page);
    await page.getByRole("button", { name: "اسلاید بعدی" }).click();
    await page.getByRole("button", { name: "اسلاید بعدی" }).click();
    await expectSlide(page, 2, true);
    const hero = await activeHero(page);
    const links = hero.getByRole("link");
    await expect(links).toHaveCount(2);
    for (const link of await links.all()) {
      const box = await link.boundingBox();
      expect(box).not.toBeNull();
      expect(box!.height).toBeGreaterThanOrEqual(44);
      expect(box!.x).toBeGreaterThanOrEqual(0);
      expect(box!.x + box!.width).toBeLessThanOrEqual(320);
    }
    await hero.screenshot({ path: shotPath("320x720", "H03") });
  });
});

test.describe("calibrated hero interactions", () => {
  test("desktop arrows, keyboard, and reduced motion stay stable", async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("requestfailed", (request) => {
      const url = request.url();
      if (url.includes("/images/hero/") || url.includes("/_next/image")) {
        errors.push(`failed ${url} ${request.failure()?.errorText ?? ""}`);
      }
    });

    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.setViewportSize({ width: 1440, height: 900 });
    await gotoHome(page);
    await expect(page.getByTestId("hero-autoplay-control")).toHaveCount(0);

    const hero = page.getByRole("region", { name: "هیرو کارزار" });
    await hero.focus();
    await page.keyboard.press("ArrowLeft");
    await expect(
      hero.getByRole("heading", { name: SLIDES[1]!.title }),
    ).toBeVisible();
    await page.getByRole("button", { name: "اسلاید قبلی" }).click();
    await expect(
      hero.getByRole("heading", { name: SLIDES[0]!.title }),
    ).toBeVisible();

    await page.waitForTimeout(1500);
    await expect(
      hero.getByRole("heading", { name: SLIDES[0]!.title }),
    ).toBeVisible();
    expect(errors).toEqual([]);
  });

  test("mobile controls advance slides and the document still scrolls", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await gotoHome(page);
    const hero = page.getByRole("region", { name: "هیرو کارزار" });
    const next = page.getByRole("button", { name: "اسلاید بعدی" });
    const prev = page.getByRole("button", { name: "اسلاید قبلی" });
    await next.click();
    await expect(hero.getByRole("heading", { name: SLIDES[1]!.title })).toBeVisible();
    await next.click();
    await expect(hero.getByRole("heading", { name: SLIDES[2]!.title })).toBeVisible();
    await prev.click();
    await expect(hero.getByRole("heading", { name: SLIDES[1]!.title })).toBeVisible();
    await expect(hero.getByRole("link", { name: SLIDES[1]!.cta })).toBeVisible();

    await expect(page.locator("footer")).toBeVisible({ timeout: 20_000 });
    await page.locator("footer").scrollIntoViewIfNeeded();
    await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(80);
    await expect(hero.getByRole("heading", { name: SLIDES[1]!.title })).toBeVisible();
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(1);
  });
});
