import { expect, test, type Page } from "@playwright/test";

const MOBILE_WIDTHS = [320, 360, 375, 390, 412, 430] as const;

const CART_STORAGE_KEY = "karzar.storefront.cart";
const SPLASH_STORAGE_KEY = "karzar-splash-seen";

async function skipFirstVisitSplash(page: Page) {
  await page.addInitScript((key) => {
    try {
      sessionStorage.setItem(key, "1");
    } catch {
      /* non-browser context */
    }
  }, SPLASH_STORAGE_KEY);
}

async function clearCart(page: Page) {
  await page.evaluate((key) => localStorage.removeItem(key), CART_STORAGE_KEY);
}

/** Stacking at the center of a locator — topmost wins pointer events. */
async function hitStackAtLocatorCenter(locator: ReturnType<Page["getByRole"]>) {
  return locator.evaluate((el) => {
    const r = el.getBoundingClientRect();
    const x = r.left + r.width / 2;
    const y = r.top + r.height / 2;
    const stack = document.elementsFromPoint(x, y);
    const atcIndex = stack.findIndex((n) => n.closest("[data-pdp-main-atc]"));
    const navIndex = stack.findIndex((n) => n.closest("nav.fixed.bottom-0"));
    const dockIndex = stack.findIndex((n) => n.closest(".mobile-dock"));
    const top = stack[0];
    return {
      x,
      y,
      atcIndex,
      navIndex,
      dockIndex,
      topTag: top?.tagName ?? null,
      isMainAtcOnTop: atcIndex === 0,
      isBottomNavOnTop: navIndex === 0,
      isStickyDockOnTop: dockIndex === 0,
      mainAtcAboveNav:
        atcIndex >= 0 && (navIndex < 0 || atcIndex < navIndex),
    };
  });
}

/** Scroll so main ATC center sits in the bottom-nav band but remains inside the viewport. */
async function scrollMainAtcIntoDockBand(mainAtc: ReturnType<Page["getByRole"]>) {
  await mainAtc.scrollIntoViewIfNeeded();
  await mainAtc.evaluate((btn) => {
    const scroller = document.scrollingElement ?? document.documentElement;
    const nav = document.querySelector("nav.fixed.bottom-0");
    if (!nav) throw new Error("missing mobile bottom nav");

    for (let attempt = 0; attempt < 12; attempt++) {
      const navRect = nav.getBoundingClientRect();
      const rect = btn.getBoundingClientRect();
      const vh = window.innerHeight;
      const half = rect.height / 2;
      const centerY = rect.top + half;
      const maxCenter = vh - half - 4;
      const minCenter = half + 4;
      const inNavBandY = navRect.top + Math.min(20, navRect.height * 0.35);
      const targetCenterY = Math.max(minCenter, Math.min(maxCenter, inNavBandY));

      if (centerY > maxCenter + 1) {
        scroller.scrollTop += centerY - maxCenter;
        continue;
      }
      if (centerY < minCenter - 1) {
        scroller.scrollTop += centerY - minCenter;
        continue;
      }
      if (Math.abs(centerY - targetCenterY) <= 2) break;
      scroller.scrollTop += centerY - targetCenterY;
    }
  });
}

async function expectMainAtcBeatsNav(mainAtc: ReturnType<Page["getByRole"]>, label: string) {
  const geometry = await mainAtc.evaluate((btn) => {
    const r = btn.getBoundingClientRect();
    const vh = window.innerHeight;
    const centerY = r.top + r.height / 2;
    return {
      centerY,
      vh,
      inViewport: centerY >= 4 && centerY <= vh - 4,
    };
  });
  expect(geometry.inViewport, `${label}: ATC center must be in viewport ${JSON.stringify(geometry)}`).toBe(
    true,
  );

  const hit = await hitStackAtLocatorCenter(mainAtc);
  expect(
    hit.mainAtcAboveNav,
    `${label}: main ATC must win over bottom nav ${JSON.stringify(hit)}`,
  ).toBe(true);
}

function mainColumnAtc(page: Page) {
  return page.locator("[data-pdp-main-atc]:visible").first();
}

test.describe("PDP mobile ATC vs bottom nav (#452)", () => {
  for (const width of MOBILE_WIDTHS) {
    test(`width ${width}: main ATC hit target not bottom nav`, async ({ page }) => {
      await skipFirstVisitSplash(page);
      await page.setViewportSize({ width, height: 844 });
      await page.goto("/product/1", { waitUntil: "domcontentloaded", timeout: 120_000 });
      await clearCart(page);
      await page.reload({ waitUntil: "domcontentloaded" });

      await expect(
        page.getByRole("heading", { level: 1, name: /دریل چکشی بوش/i }),
      ).toBeVisible({ timeout: 30_000 });

      const mainAtc = mainColumnAtc(page);
      await expect(mainAtc).toBeVisible({ timeout: 15_000 });

      await scrollMainAtcIntoDockBand(mainAtc);
      await expectMainAtcBeatsNav(mainAtc, `width ${width}px`);

      await mainAtc.click({ timeout: 5_000 });
      await page.waitForFunction(
        (key) => {
          try {
            const raw = localStorage.getItem(key);
            if (!raw) return false;
            const parsed = JSON.parse(raw) as {
              state?: { stash?: { cart?: unknown[] }; cart?: unknown[] };
            };
            const stashLen = parsed.state?.stash?.cart?.length ?? 0;
            const legacyLen = parsed.state?.cart?.length ?? 0;
            return stashLen > 0 || legacyLen > 0;
          } catch {
            return false;
          }
        },
        CART_STORAGE_KEY,
        { timeout: 10_000 },
      );
    });
  }

  test("width 390: sticky dock ATC clickable", async ({ page }) => {
    await skipFirstVisitSplash(page);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/product/1", { waitUntil: "domcontentloaded", timeout: 120_000 });
    await clearCart(page);
    await page.reload({ waitUntil: "domcontentloaded" });

    const stickyAdd = page
      .locator(".mobile-dock")
      .getByRole("button", { name: /افزودن به سبد خرید/i })
      .first();
    await expect(stickyAdd).toBeVisible({ timeout: 15_000 });

    const hit = await hitStackAtLocatorCenter(stickyAdd);
    expect(hit.dockIndex).toBeGreaterThanOrEqual(0);
    expect(
      hit.navIndex < 0 || hit.dockIndex < hit.navIndex,
      `sticky dock must beat bottom nav: ${JSON.stringify(hit)}`,
    ).toBe(true);

    await stickyAdd.click();
    await page.waitForFunction(
      (key) => {
        try {
          const raw = localStorage.getItem(key);
          if (!raw) return false;
          const parsed = JSON.parse(raw) as {
            state?: { stash?: { cart?: unknown[] }; cart?: unknown[] };
          };
          return (parsed.state?.stash?.cart?.length ?? 0) > 0;
        } catch {
          return false;
        }
      },
      CART_STORAGE_KEY,
      { timeout: 10_000 },
    );
  });

  test("width 768 secondary: main ATC above bottom nav in dock band", async ({ page }) => {
    await skipFirstVisitSplash(page);
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto("/product/1", { waitUntil: "domcontentloaded", timeout: 120_000 });
    await clearCart(page);
    await page.reload({ waitUntil: "domcontentloaded" });

    const mainAtc = mainColumnAtc(page);
    await expect(mainAtc).toBeVisible({ timeout: 15_000 });
    await scrollMainAtcIntoDockBand(mainAtc);
    await expectMainAtcBeatsNav(mainAtc, "width 768px");
  });

  test("width 390: bottom nav cart link clickable", async ({ page }) => {
    await skipFirstVisitSplash(page);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/product/1", { waitUntil: "domcontentloaded", timeout: 120_000 });
    await clearCart(page);

    const cartNav = page.getByRole("link", { name: /^سبد$/i }).last();
    await expect(cartNav).toBeVisible({ timeout: 15_000 });
    await cartNav.click();
    await expect(page).toHaveURL(/\/cart/, { timeout: 15_000 });
  });
});
