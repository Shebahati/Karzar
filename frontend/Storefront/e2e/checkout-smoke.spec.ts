import { expect, test, type Page } from "@playwright/test";

const CART_STORAGE_KEY = "karzar.storefront.cart";

/** Wait until Zustand persist has written at least one purchase line. */
async function waitForCartPersisted(page: Page) {
  await page.waitForFunction(
    (key) => {
      try {
        const raw = localStorage.getItem(key);
        if (!raw) return false;
        const parsed = JSON.parse(raw) as { state?: { cart?: unknown[] } };
        return (parsed.state?.cart?.length ?? 0) > 0;
      } catch {
        return false;
      }
    },
    CART_STORAGE_KEY,
    { timeout: 10_000 },
  );
}

/**
 * Smoke: OTP login at checkout → submit → payment callback success path (mock).
 * Requires NEXT_PUBLIC_USE_MOCK=true (injected by playwright.config webServer).
 */
test.describe("checkout smoke (mock)", () => {
  test.setTimeout(90_000);

  test("OTP → checkout → payment callback", async ({ page }) => {
    await page.goto("/product/1");
    await expect(
      page.getByRole("heading", { level: 1, name: /دریل چکشی بوش/i }),
    ).toBeVisible({ timeout: 30_000 });

    const addCart = page.getByRole("button", { name: /افزودن به سبد خرید/i });
    await expect(addCart).toBeVisible({ timeout: 15_000 });
    await addCart.click();
    await waitForCartPersisted(page);

    await page.goto("/checkout");
    // Hydration: empty-cart flash must resolve to auth step in mock mode.
    await expect(
      page.getByRole("heading", { level: 2, name: "ورود برای پرداخت" }),
    ).toBeVisible({ timeout: 20_000 });

    const phoneInput = page.locator('input[inputmode="tel"]').first();
    await phoneInput.fill("09123456789");
    await page.getByRole("button", { name: /دریافت کد/i }).click();

    // OTP — mock code 11111
    const otpInput = page.locator('input[inputmode="numeric"]').first();
    await expect(otpInput).toBeVisible({ timeout: 15_000 });
    await otpInput.fill("11111");
    await page.getByRole("button", { name: /تأیید و ادامه/i }).click();

    // Shipping (purchase)
    await expect(
      page.getByRole("heading", { level: 2, name: "اطلاعات ارسال" }),
    ).toBeVisible({ timeout: 20_000 });

    const shipping = page.locator("form").filter({
      has: page.getByRole("heading", { level: 2, name: "اطلاعات ارسال" }),
    });
    await shipping.getByLabel(/نام و نام خانوادگی/i).fill("کاربر آزمایشی");
    await shipping.getByLabel(/^استان$/i).fill("تهران");
    await shipping.getByLabel(/^شهر$/i).fill("تهران");
    await shipping.getByLabel(/کد پستی/i).fill("1234567890");
    await shipping.getByLabel(/نشانی کامل/i).fill("خیابان ولیعصر پلاک ۱۲۳ واحد ۴");

    await shipping.getByRole("button", { name: /انتقال به درگاه پرداخت/i }).click();

    // Mock payment redirects to callback → success
    await page.waitForURL(/checkout\/(success|payment\/callback)/, {
      timeout: 45_000,
    });
    const url = page.url();
    expect(url).toMatch(/checkout\/(success|payment\/callback)/);

    // Prefer landing on success after verify; callback is acceptable mid-flight.
    if (/payment\/callback/.test(url)) {
      await page.waitForURL(/checkout\/success/, { timeout: 30_000 });
    }
    await expect(page).toHaveURL(/checkout\/success/);
  });
});
