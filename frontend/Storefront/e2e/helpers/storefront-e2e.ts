import { expect, type Page } from "@playwright/test";

export const MOBILE_WIDTHS = [320, 360, 375, 390, 412, 430] as const;

export const MOBILE_HEIGHT = 844;

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
  const productTitle = productCardLink.getByRole("heading", { level: 3 });
  await expect(productTitle).toBeVisible({ timeout: 15_000 });
  await productTitle.click();
  await expect(page).toHaveURL(/\/product\//, { timeout: 60_000 });

  await expect(
    page.getByRole("heading", { level: 1, name: E2E_CATALOG_PRODUCT_NAME }),
  ).toBeVisible({ timeout: 60_000 });
}

export async function openCartViaMobileUi(page: Page) {
  const bottomNav = page.getByRole("navigation", { name: "ناوبری پایین" });
  const cartFromNav = bottomNav.getByRole("link", { name: /سبد/i });

  const bottomNavCartVisible = await cartFromNav
    .waitFor({ state: "visible", timeout: 8_000 })
    .then(() => true)
    .catch(() => false);

  if (bottomNavCartVisible) {
    await cartFromNav.click();
    await expect(page).toHaveURL(/\/cart/, { timeout: 15_000 });
    return;
  }

  const footerCart = page.getByRole("contentinfo").getByRole("link", { name: "سبد خرید" });
  await footerCart.scrollIntoViewIfNeeded();
  await expect(footerCart).toBeVisible({ timeout: 15_000 });
  await footerCart.click();
  await expect(page).toHaveURL(/\/cart/, { timeout: 15_000 });
}

export async function addToCartFromPdp(page: Page) {
  const addCart = page.getByRole("button", { name: /افزودن به سبد خرید/i }).first();
  await expect(addCart).toBeVisible({ timeout: 15_000 });
  await expect(addCart).toBeEnabled();
  await addCart.scrollIntoViewIfNeeded();
  await addCart.click({ timeout: 10_000 });
  await waitForCartPersisted(page);
}

/** One ATC action → line quantity exactly 1 (QtyStepper UI, not store internals). */
export async function assertCartLineQuantityIsOne(page: Page, productName: RegExp) {
  const line = page.getByRole("article").filter({ hasText: productName });
  await expect(line).toBeVisible({ timeout: 15_000 });

  const mobileStepperQty = line
    .locator("div.sm\\:hidden")
    .locator('button[aria-label="کاهش تعداد"] + span.tnum');
  await expect(mobileStepperQty).toHaveText("۱");
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
