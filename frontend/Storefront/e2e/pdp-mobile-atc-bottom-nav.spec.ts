import { expect, test, type Locator, type Page } from "@playwright/test";

const MOBILE_WIDTHS = [320, 360, 375, 390, 412, 430] as const;

const CART_STORAGE_KEY = "karzar.storefront.cart";
const SPLASH_STORAGE_KEY = "karzar-splash-seen";

type Rect = { top: number; left: number; right: number; bottom: number; width: number; height: number };

type HitStack = {
  x: number;
  y: number;
  inViewport: boolean;
  atcIndex: number;
  navIndex: number;
  dockIndex: number;
  purchaseIndex: number;
  buyColumnIndex: number;
  topTag: string | null;
  mainAtcAboveNav: boolean;
  buyColumnIsTopHit: boolean;
};

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

async function openPdp(page: Page, width: number, height: number) {
  await skipFirstVisitSplash(page);
  await page.setViewportSize({ width, height });
  await page.goto("/product/1", { waitUntil: "domcontentloaded", timeout: 120_000 });
  await clearCart(page);
  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(
    page.getByRole("heading", { level: 1, name: /دریل چکشی بوش/i }),
  ).toBeVisible({ timeout: 30_000 });
}

function mainColumnAtc(page: Page) {
  return page.locator("[data-pdp-main-atc]:visible").first();
}

function hitStackFromPoint(page: Page, x: number, y: number): Promise<HitStack> {
  return page.evaluate(({ px, py }) => {
    const vh = window.innerHeight;
    const vw = window.innerWidth;
    const inViewport = px >= 0 && py >= 0 && px <= vw && py <= vh;
    const stack = inViewport ? document.elementsFromPoint(px, py) : [];
    const atcIndex = stack.findIndex((n) => n.closest("[data-pdp-main-atc]"));
    const navIndex = stack.findIndex((n) => n.closest("nav.fixed.bottom-0"));
    const dockIndex = stack.findIndex((n) => n.closest(".mobile-dock"));
    const purchaseIndex = stack.findIndex((n) => n.closest("[data-pdp-main-purchase]"));
    const buyColumnIndex = stack.findIndex((n) => {
      const col = n.closest("[data-pdp-main-buy]");
      return Boolean(col) && !n.closest("[data-pdp-main-purchase]") && !n.closest("[data-pdp-main-atc]");
    });
    const top = stack[0] as Element | undefined;
    const buyColTop =
      Boolean(top?.matches("[data-pdp-main-buy]")) ||
      Boolean(
        top?.closest("[data-pdp-main-buy]") &&
          !top?.closest("[data-pdp-main-purchase]") &&
          !top?.closest("[data-pdp-main-atc]") &&
          !top?.closest("button"),
      );
    return {
      x: px,
      y: py,
      inViewport,
      atcIndex,
      navIndex,
      dockIndex,
      purchaseIndex,
      buyColumnIndex,
      topTag: top?.tagName ?? null,
      mainAtcAboveNav: atcIndex >= 0 && (navIndex < 0 || atcIndex < navIndex),
      buyColumnIsTopHit: buyColTop,
    };
  }, { px: x, py: y });
}

async function hitStackAtLocatorCenter(locator: Locator): Promise<HitStack> {
  return locator.evaluate((btn) => {
    const r = btn.getBoundingClientRect();
    const fractions: Array<[number, number]> = [
      [0.5, 0.55],
      [0.5, 0.72],
      [0.5, 0.4],
      [0.35, 0.55],
      [0.65, 0.55],
    ];

    const vh = window.innerHeight;
    const vw = window.innerWidth;

    for (const [fx, fy] of fractions) {
      const x = r.left + r.width * fx;
      const y = r.top + r.height * fy;
      const inViewport = x >= 0 && y >= 0 && x <= vw && y <= vh;
      if (!inViewport) continue;

      const stack = document.elementsFromPoint(x, y);
      const buttonIndex = stack.indexOf(btn);
      const atcIndex = stack.findIndex(
        (n) => n === btn || n.closest("[data-pdp-main-atc]") === btn,
      );
      if (atcIndex < 0 && buttonIndex < 0) continue;

      const navIndex = stack.findIndex((n) => n.closest("nav.fixed.bottom-0"));
      const dockIndex = stack.findIndex((n) => n.closest(".mobile-dock"));
      const purchaseIndex = stack.findIndex((n) => n.closest("[data-pdp-main-purchase]"));
      const buyColumnIndex = stack.findIndex((n) => {
        const col = n.closest("[data-pdp-main-buy]");
        return Boolean(col) && !n.closest("[data-pdp-main-purchase]") && n !== btn && !btn.contains(n);
      });
      const top = stack[0] as Element | undefined;
      const buyColTop =
        Boolean(top?.matches("[data-pdp-main-buy]")) ||
        Boolean(
          top?.closest("[data-pdp-main-buy]") &&
            !top?.closest("[data-pdp-main-purchase]") &&
            top !== btn &&
            !btn.contains(top),
        );

      const hitIndex = atcIndex >= 0 ? atcIndex : buttonIndex;
      return {
        x,
        y,
        inViewport: true,
        atcIndex: hitIndex,
        navIndex,
        dockIndex,
        purchaseIndex,
        buyColumnIndex,
        topTag: top?.tagName ?? null,
        mainAtcAboveNav: hitIndex >= 0 && (navIndex < 0 || hitIndex < navIndex),
        buyColumnIsTopHit: buyColTop,
      };
    }

    const x = r.left + r.width / 2;
    const y = r.top + r.height / 2;
    return {
      x,
      y,
      inViewport: x >= 0 && y >= 0 && x <= vw && y <= vh,
      atcIndex: -1,
      navIndex: -1,
      dockIndex: -1,
      purchaseIndex: -1,
      buyColumnIndex: -1,
      topTag: null,
      mainAtcAboveNav: false,
      buyColumnIsTopHit: true,
    };
  });
}

async function scrollMainAtcIntoDockBand(mainAtc: Locator) {
  await mainAtc.scrollIntoViewIfNeeded();
  await mainAtc.evaluate((btn) => {
    const scroller = document.scrollingElement ?? document.documentElement;
    const nav = document.querySelector("nav.fixed.bottom-0");
    if (!nav) throw new Error("missing mobile bottom nav");

    for (let attempt = 0; attempt < 16; attempt++) {
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
      if (Math.abs(centerY - targetCenterY) <= 2) {
        const overlapsNav = rect.bottom > navRect.top + 4;
        if (overlapsNav) break;
      }
      scroller.scrollTop += centerY - targetCenterY;
    }
  });
}

async function scrollMainAtcUnderStickyDock(mainAtc: Locator) {
  await mainAtc.scrollIntoViewIfNeeded();
  await mainAtc.evaluate((btn) => {
    const scroller = document.scrollingElement ?? document.documentElement;
    const dock = document.querySelector(".mobile-dock");
    if (!dock) throw new Error("missing sticky dock");

    for (let attempt = 0; attempt < 14; attempt++) {
      const dockRect = dock.getBoundingClientRect();
      const rect = btn.getBoundingClientRect();
      const vh = window.innerHeight;
      const half = rect.height / 2;
      const centerY = rect.top + half;
      const maxCenter = vh - half - 4;
      const minCenter = half + 4;
      const targetCenterY = Math.max(
        minCenter,
        Math.min(maxCenter, dockRect.top + dockRect.height * 0.55),
      );

      if (centerY > maxCenter + 1) {
        scroller.scrollTop += centerY - maxCenter;
        continue;
      }
      if (centerY < minCenter - 1) {
        scroller.scrollTop += centerY - minCenter;
        continue;
      }
      if (Math.abs(centerY - targetCenterY) <= 3) break;
      scroller.scrollTop += centerY - targetCenterY;
    }
  });
}

async function expectMainAtcBeatsNav(mainAtc: Locator, label: string) {
  const hit = await hitStackAtLocatorCenter(mainAtc);
  expect(hit.inViewport, `${label}: point in viewport ${JSON.stringify(hit)}`).toBe(true);
  expect(hit.atcIndex, `${label}: ATC must be in hit stack ${JSON.stringify(hit)}`).toBeGreaterThanOrEqual(
    0,
  );
  expect(hit.mainAtcAboveNav, `${label}: main ATC over nav ${JSON.stringify(hit)}`).toBe(true);
  expect(hit.buyColumnIsTopHit, `${label}: buy column must not own hit ${JSON.stringify(hit)}`).toBe(
    false,
  );
  expect(hit.purchaseIndex, `${label}: purchase region in stack ${JSON.stringify(hit)}`).toBeGreaterThanOrEqual(
    0,
  );
}

async function measureStackingRects(page: Page) {
  return page.evaluate(() => {
    const viewport = { width: window.innerWidth, height: window.innerHeight };
    const toRect = (el: Element | null): Rect | null => {
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return {
        top: r.top,
        left: r.left,
        right: r.right,
        bottom: r.bottom,
        width: r.width,
        height: r.height,
      };
    };
    const atc = document.querySelector("[data-pdp-main-atc]");
    const buyCol = document.querySelector("[data-pdp-main-buy]");
    const dock = document.querySelector(".mobile-dock");
    const nav = document.querySelector("nav.fixed.bottom-0");
    return {
      viewport,
      mainAtc: toRect(atc),
      buyColumn: toRect(buyCol),
      stickyDock: toRect(dock),
      bottomNav: toRect(nav),
    };
  });
}

function rectsOverlap(a: Rect, b: Rect) {
  return a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
}

test.describe("PDP mobile ATC vs bottom nav (#452)", () => {
  for (const width of MOBILE_WIDTHS) {
    test(`width ${width}: main ATC hit target not bottom nav`, async ({ page }) => {
      await openPdp(page, width, 844);

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

  test("width 390: concurrent stacking contract", async ({ page }) => {
    await openPdp(page, 390, 844);

    const mainAtc = mainColumnAtc(page);
    await expect(mainAtc).toBeVisible({ timeout: 15_000 });

    await scrollMainAtcIntoDockBand(mainAtc);
    const rectsAfterNav = await measureStackingRects(page);
    const mainHitNavBand = await hitStackAtLocatorCenter(mainAtc);

    expect(mainHitNavBand.inViewport).toBe(true);
    expect(mainHitNavBand.mainAtcAboveNav).toBe(true);
    expect(mainHitNavBand.buyColumnIsTopHit).toBe(false);
    expect(mainHitNavBand.atcIndex).toBeGreaterThanOrEqual(0);

    await scrollMainAtcUnderStickyDock(mainAtc);
    const rectsSticky = await measureStackingRects(page);
    const mainAtcRect = rectsSticky.mainAtc;
    const dockRect = rectsSticky.stickyDock;
    expect(mainAtcRect).not.toBeNull();
    expect(dockRect).not.toBeNull();

    if (mainAtcRect && dockRect && rectsOverlap(mainAtcRect, dockRect)) {
      const stickyBtn = page
        .locator(".mobile-dock")
        .getByRole("button", { name: /افزودن به سبد خرید/i })
        .first();
      const stickyHit = await hitStackAtLocatorCenter(stickyBtn);
      expect(stickyHit.inViewport).toBe(true);
      expect(stickyHit.dockIndex).toBeGreaterThanOrEqual(0);
      expect(
        stickyHit.dockIndex < stickyHit.atcIndex || stickyHit.atcIndex < 0,
        `sticky must beat main when overlapping: ${JSON.stringify(stickyHit)}`,
      ).toBe(true);

      const mainHitUnderDock = await hitStackAtLocatorCenter(mainAtc);
      expect(mainHitUnderDock.inViewport).toBe(true);
      expect(
        mainHitUnderDock.dockIndex >= 0 &&
          (mainHitUnderDock.atcIndex < 0 || mainHitUnderDock.dockIndex < mainHitUnderDock.atcIndex),
        `sticky owns overlap with main ATC: ${JSON.stringify(mainHitUnderDock)}`,
      ).toBe(true);
    }

    const homeNav = page.getByRole("link", { name: /^خانه$/i }).last();
    await expect(homeNav).toBeVisible();
    const navPoint = await homeNav.evaluate((el) => {
      const r = el.getBoundingClientRect();
      const atc = document.querySelector("[data-pdp-main-atc]");
      const ar = atc?.getBoundingClientRect();
      const cx = r.left + r.width / 2;
      const cy = r.top + r.height / 2;
      const overlapsAtc =
        ar &&
        cx >= ar.left &&
        cx <= ar.right &&
        cy >= ar.top &&
        cy <= ar.bottom;
      return { x: cx, y: cy, overlapsAtc };
    });
    expect(navPoint.overlapsAtc).toBe(false);

    const navHit = await hitStackFromPoint(page, navPoint.x, navPoint.y);
    expect(navHit.inViewport).toBe(true);
    expect(navHit.navIndex).toBeGreaterThanOrEqual(0);
    expect(navHit.navIndex).toBeLessThanOrEqual(2);

    expect(rectsAfterNav.buyColumn).not.toBeNull();
    expect(rectsAfterNav.bottomNav).not.toBeNull();
  });

  test("width 390: sticky dock ATC clickable", async ({ page }) => {
    await openPdp(page, 390, 844);

    const stickyAdd = page
      .locator(".mobile-dock")
      .getByRole("button", { name: /افزودن به سبد خرید/i })
      .first();
    await expect(stickyAdd).toBeVisible({ timeout: 15_000 });

    const hit = await hitStackAtLocatorCenter(stickyAdd);
    expect(hit.inViewport).toBe(true);
    expect(hit.dockIndex).toBeGreaterThanOrEqual(0);
    expect(hit.navIndex < 0 || hit.dockIndex < hit.navIndex).toBe(true);

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
    await openPdp(page, 768, 1024);

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
