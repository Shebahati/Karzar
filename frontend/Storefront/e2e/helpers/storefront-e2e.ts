import { expect, type Locator, type Page } from "@playwright/test";

export const MOBILE_WIDTHS = [320, 360, 375, 390, 412, 430] as const;

export const MOBILE_HEIGHT = 844;

/** KEYBOARD_LAYOUT_PROXY — simulates reduced visual space when OS keyboard is open (not a real keyboard). */
export const KEYBOARD_LAYOUT_PROXY_HEIGHT = 480;

export const CART_STORAGE_KEY = "karzar.storefront.cart";
export const SPLASH_STORAGE_KEY = "karzar-splash-seen";

export const MOCK_PHONE = "09123456789";
export const MOCK_OTP = "111111";

/** Mock PLP rows use SEO crawl fixtures (non-placeholder image); drill SKU is PDP-only in mock. */
export const E2E_CATALOG_SEARCH_TERM = "crawl";
export const E2E_CATALOG_PRODUCT_NAME = /محصول crawl آزمایشی 45/i;

export const PERSIAN_CHECKOUT = {
  fullName: "کاربر آزمایشی",
  province: "تهران",
  city: "تهران",
  postalCode: "1234567890",
  address: "خیابان ولیعصر پلاک ۱۲۳ واحد ۴",
} as const;

export async function skipFirstVisitSplash(page: Page) {
  await page.addInitScript((key) => {
    try {
      sessionStorage.setItem(key, "1");
    } catch {
      /* non-browser */
    }
  }, SPLASH_STORAGE_KEY);
}

export async function clearCart(page: Page) {
  await page.evaluate((key) => localStorage.removeItem(key), CART_STORAGE_KEY);
}

export async function waitForCartPersisted(page: Page, timeoutMs = 20_000) {
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
    { timeout: timeoutMs },
  );
}

export async function assertNoHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(() => {
    const doc = document.documentElement;
    return doc.scrollWidth - doc.clientWidth;
  });
  expect(overflow, "document horizontal overflow").toBeLessThanOrEqual(2);
}

type HitProbe = {
  inViewport: boolean;
  targetIndex: number;
  navIndex: number;
  dockIndex: number;
};

export async function hitProbeAtLocatorCenter(locator: Locator): Promise<HitProbe> {
  return locator.evaluate((el) => {
    const r = el.getBoundingClientRect();
    const x = r.left + r.width / 2;
    const y = r.top + r.height / 2;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const inViewport = x >= 0 && y >= 0 && x <= vw && y <= vh;
    const stack = inViewport ? document.elementsFromPoint(x, y) : [];
    const targetIndex = stack.findIndex((n) => n === el || el.contains(n));
    const navIndex = stack.findIndex((n) => n.closest("nav.fixed.bottom-0"));
    const dockIndex = stack.findIndex((n) => n.closest(".mobile-dock"));
    return { inViewport, targetIndex, navIndex, dockIndex };
  });
}

/** CTA must be hittable and not lose to bottom nav at its center point. */
export async function assertCtaNotInterceptedByBottomNav(cta: Locator, label: string) {
  const hit = await hitProbeAtLocatorCenter(cta);
  expect(hit.inViewport, `${label}: in viewport ${JSON.stringify(hit)}`).toBe(true);
  expect(hit.targetIndex, `${label}: in hit stack`).toBeGreaterThanOrEqual(0);
  expect(
    hit.navIndex < 0 || hit.targetIndex < hit.navIndex,
    `${label}: bottom nav must not beat CTA ${JSON.stringify(hit)}`,
  ).toBe(true);
}

/** Checkout pay CTA lives inside `.mobile-dock`; assert reachability without nav interception. */
export async function assertMobilePayCtaReachable(page: Page, label: string) {
  const payCta = mobilePayCta(page);
  await payCta.scrollIntoViewIfNeeded();
  await expect(payCta, `${label}: visible`).toBeVisible();
  await expect(payCta, `${label}: enabled`).toBeEnabled();
  const hit = await hitProbeAtLocatorCenter(payCta);
  expect(hit.inViewport, `${label}: in viewport`).toBe(true);
  expect(hit.dockIndex, `${label}: dock in stack`).toBeGreaterThanOrEqual(0);
}

/** Scroll so the field sits above fixed bottom nav / mobile checkout dock. */
export async function scrollFieldAboveMobileChrome(field: Locator) {
  await field.scrollIntoViewIfNeeded();
  await field.evaluate((el) => {
    const blockers = [
      document.querySelector("nav.fixed.bottom-0"),
      document.querySelector(".mobile-dock"),
    ].filter(Boolean) as Element[];
    if (blockers.length === 0) return;
    const minTop = Math.min(...blockers.map((b) => b.getBoundingClientRect().top));
    const r = el.getBoundingClientRect();
    const pad = 8;
    const overflow = r.bottom - (minTop - pad);
    if (overflow > 0) {
      window.scrollBy({ top: overflow, left: 0 });
    }
  });
}

export async function assertFieldCenterAboveBottomNav(field: Locator, label: string) {
  await scrollFieldAboveMobileChrome(field);
  const ok = await field.evaluate((el) => {
    const nav = document.querySelector("nav.fixed.bottom-0");
    const dock = document.querySelector(".mobile-dock");
    const r = el.getBoundingClientRect();
    const cy = r.top + r.height / 2;
    const blockers = [nav, dock].filter(Boolean) as Element[];
    if (blockers.length === 0) return true;
    const minTop = Math.min(
      ...blockers.map((b) => b.getBoundingClientRect().top),
    );
    return cy < minTop - 2;
  });
  expect(ok, `${label}: field center not under fixed bottom chrome`).toBe(true);
}

/**
 * KEYBOARD_LAYOUT_PROXY — automated stand-in for virtual keyboard overlap checks.
 * Not PHYSICAL_KEYBOARD_PASS.
 */
export async function runKeyboardLayoutProxy(
  page: Page,
  width: number,
  field: Locator,
  cta: Locator,
  label: string,
) {
  await page.setViewportSize({ width, height: MOBILE_HEIGHT });
  await field.focus();
  await expect(field).toBeVisible();
  await field.scrollIntoViewIfNeeded();

  await page.setViewportSize({ width, height: KEYBOARD_LAYOUT_PROXY_HEIGHT });
  await scrollFieldAboveMobileChrome(field);
  await expect(field).toBeVisible();
  await assertFieldCenterAboveBottomNav(field, `${label}: proxy height`);

  await cta.scrollIntoViewIfNeeded();
  await expect(cta).toBeVisible();
  await expect(cta).toBeEnabled();

  await page.setViewportSize({ width, height: MOBILE_HEIGHT });
}

export async function mockOtpLoginAtCheckout(page: Page) {
  await expect(
    page.getByRole("heading", { level: 2, name: "ورود برای پرداخت" }),
  ).toBeVisible({ timeout: 20_000 });

  const phoneInput = page.locator('input[inputmode="tel"]').first();
  await phoneInput.fill(MOCK_PHONE);
  await page.getByRole("button", { name: /دریافت کد/i }).click();

  const otpInput = page.locator('input[inputmode="numeric"]').first();
  await expect(otpInput).toBeVisible({ timeout: 15_000 });
  await otpInput.fill(MOCK_OTP);
  await page.getByRole("button", { name: /تأیید و ادامه/i }).click();
}

export async function fillPersianShippingForm(page: Page) {
  await expect(
    page.getByRole("heading", { level: 2, name: "اطلاعات ارسال" }),
  ).toBeVisible({ timeout: 20_000 });

  const shipping = page.locator("form").filter({
    has: page.getByRole("heading", { level: 2, name: "اطلاعات ارسال" }),
  });

  await shipping.getByLabel(/^استان$/i).fill(PERSIAN_CHECKOUT.province);
  await shipping.getByLabel(/^شهر$/i).fill(PERSIAN_CHECKOUT.city);
  await shipping.getByLabel(/کد پستی/i).fill(PERSIAN_CHECKOUT.postalCode);
  await shipping.getByLabel(/نشانی کامل/i).fill(PERSIAN_CHECKOUT.address);
  await shipping.getByLabel(/نام و نام خانوادگی/i).fill(PERSIAN_CHECKOUT.fullName);

  await expect(shipping.getByLabel(/نام و نام خانوادگی/i)).toHaveValue(
    PERSIAN_CHECKOUT.fullName,
  );
  await expect(shipping.getByLabel(/نشانی کامل/i)).toHaveValue(PERSIAN_CHECKOUT.address);

  const tipax = page.getByRole("radio", { name: /تیپاکس/i });
  await expect(tipax).toBeVisible({ timeout: 15_000 });
  await tipax.click();

  return shipping;
}

export function mobilePayCta(page: Page) {
  return page.locator(".mobile-dock").getByRole("button", { name: /^پرداخت$/ });
}

/** Mobile dock uses «تکمیل خرید»; desktop summary uses «تکمیل خرید و پرداخت». */
export function cartCheckoutCta(page: Page) {
  return page.getByRole("button", { name: /تکمیل خرید( و پرداخت)?$/ });
}

export async function openPdpViaSearch(page: Page) {
  if (!page.url().includes("127.0.0.1")) {
    await page.goto("/", { waitUntil: "domcontentloaded", timeout: 120_000 });
  }
  await assertNoHorizontalOverflow(page);

  const searchOpen = page.getByRole("button", { name: "جستجو" }).first();
  await expect(searchOpen).toBeVisible({ timeout: 15_000 });
  await searchOpen.click();

  const searchDialog = page.getByRole("dialog", { name: "جستجوی کارزار" });
  await expect(searchDialog).toBeVisible({ timeout: 10_000 });
  const searchBox = searchDialog.getByPlaceholder(/جستجوی ابزار/i);
  await expect(searchBox).toBeVisible();

  await searchBox.fill(E2E_CATALOG_SEARCH_TERM);
  await expect(searchDialog.getByText(/در حال جستجو/i)).toHaveCount(0, {
    timeout: 30_000,
  });

  const spotlightProduct = searchDialog
    .getByRole("button")
    .filter({ hasText: /محصول crawl آزمایشی/i })
    .first();
  await expect(
    spotlightProduct,
    "spotlight search must list PLP-visible mock crawl products",
  ).toBeVisible({ timeout: 45_000 });

  const viewAll = searchDialog.getByRole("button", { name: /مشاهده همه نتایج/i });
  await expect(viewAll).toBeVisible({ timeout: 15_000 });
  await viewAll.click();

  await expect(page).toHaveURL(/\/catalog/, { timeout: 15_000 });
  await expect(page).toHaveURL(/search=/i, { timeout: 15_000 });
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: new RegExp(`نتایج «${E2E_CATALOG_SEARCH_TERM}»`, "i"),
    }),
  ).toBeVisible({ timeout: 15_000 });
  await assertNoHorizontalOverflow(page);

  const catalogMain = page.getByRole("main");
  await expect(
    catalogMain.getByText(/با این فیلترها محصولی پیدا نشد/i),
    "catalog PLP must not be empty for mock crawl search",
  ).toHaveCount(0);

  const productCardLink = catalogMain
    .getByRole("link", { name: E2E_CATALOG_PRODUCT_NAME })
    .first();
  await expect(
    productCardLink,
    "catalog PLP must expose a clickable product card after search",
  ).toBeVisible({ timeout: 60_000 });

  await productCardLink.scrollIntoViewIfNeeded();
  await Promise.all([
    page.waitForURL(/\/product\//, { timeout: 60_000 }),
    productCardLink.click(),
  ]);

  await expect(
    page.getByRole("heading", { level: 1, name: E2E_CATALOG_PRODUCT_NAME }),
  ).toBeVisible({ timeout: 60_000 });
}

export async function openCartViaMobileUi(page: Page) {
  const bottomNav = page.getByRole("navigation", { name: "ناوبری پایین" });
  const cartFromNav = bottomNav.getByRole("link", { name: /سبد/i });

  try {
    await expect(cartFromNav).toBeVisible({ timeout: 5_000 });
    await cartFromNav.click();
  } catch {
    const footerCart = page.getByRole("contentinfo").getByRole("link", { name: "سبد خرید" });
    await footerCart.scrollIntoViewIfNeeded();
    await expect(footerCart).toBeVisible({ timeout: 15_000 });
    await footerCart.click();
  }
  await expect(page).toHaveURL(/\/cart/, { timeout: 15_000 });
}

export async function addToCartFromPdp(page: Page) {
  const addCart = page.getByRole("button", { name: /افزودن به سبد خرید/i }).first();
  await expect(addCart).toBeVisible({ timeout: 15_000 });
  await expect(addCart).toBeEnabled();
  await addCart.scrollIntoViewIfNeeded();

  for (let attempt = 0; attempt < 2; attempt++) {
    await addCart.click({ timeout: 10_000 });
    try {
      await waitForCartPersisted(page);
      return;
    } catch (err) {
      if (attempt === 1) throw err;
    }
  }
}

/** MOCK_MATRIX_RETURN_PASS — mock UI only; not live payment idempotency (#242). */
export async function mockCheckoutSuccessWithRefresh(page: Page) {
  await expect(page).toHaveURL(/checkout\/(success|payment\/callback)/, {
    timeout: 45_000,
  });
  if (/payment\/callback/.test(page.url())) {
    await expect(page).toHaveURL(/checkout\/success/, { timeout: 30_000 });
  }
  await expect(page).toHaveURL(/checkout\/success/);

  const successHeading = page.getByRole("heading", {
    level: 1,
    name: /پرداخت با موفقیت انجام شد/i,
  });
  await expect(successHeading).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("کد پیگیری")).toBeVisible();

  const successUrl = page.url();
  expect(successUrl).toMatch(/checkout\/success/);
  expect(successUrl).not.toMatch(/sep|payment\/init/i);

  await page.reload({ waitUntil: "domcontentloaded" });

  await expect(page).toHaveURL(/checkout\/success/);
  expect(page.url()).not.toMatch(/payment\/callback|sep|payment\/init/i);
  await expect(successHeading).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("کد پیگیری")).toBeVisible();
}
