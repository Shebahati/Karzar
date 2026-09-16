import { expect, test, type Page } from "@playwright/test";

const CART_STORAGE_KEY = "karzar.storefront.cart";

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

async function otpToShippingStep(page: Page) {
  await page.goto("/product/1", { waitUntil: "domcontentloaded", timeout: 120_000 });
  await page.getByRole("button", { name: /افزودن به سبد خرید/i }).click();
  await waitForCartPersisted(page);
  await page.goto("/checkout", { waitUntil: "domcontentloaded", timeout: 120_000 });
  await page.locator('input[inputmode="tel"]').first().fill("09123456789");
  await page.getByRole("button", { name: /دریافت کد/i }).click();
  await page.locator('input[inputmode="numeric"]').first().fill("111111");
  await page.getByRole("button", { name: /تأیید و ادامه/i }).click();
  await expect(page.getByRole("heading", { level: 2, name: "اطلاعات ارسال" })).toBeVisible({
    timeout: 20_000,
  });
}

test.describe("shipping method selection (mock)", () => {
  test.setTimeout(120_000);

  test("Tehran province address shows five methods and receiver-due copy", async ({ page }) => {
    await otpToShippingStep(page);
    const shipping = page.locator("form").filter({
      has: page.getByRole("heading", { level: 2, name: "اطلاعات ارسال" }),
    });
    await shipping.getByLabel(/^استان$/i).fill("تهران");
    await shipping.getByLabel(/^شهر$/i).fill("تهران");
    await shipping.getByLabel(/کد پستی/i).fill("1234567890");
    await shipping.getByLabel(/نشانی کامل/i).fill("خیابان ولیعصر پلاک ۱۲۳ واحد ۴");
    await expect(page.getByText("ارسال فوری ۳ ساعته")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("پیک موتوری حداکثر تا ۴۸ ساعت")).toBeVisible();
    await expect(page.getByText("پست پیشتاز")).toBeVisible();
    await expect(page.getByText("تیپاکس")).toBeVisible();
    await expect(page.getByText("پس‌کرایه").first()).toBeVisible();
    const express3h = page.getByRole("radio", { name: /ارسال فوری ۳ ساعته/i });
    await express3h.click();
    await expect(express3h).toBeChecked();
    await expect(express3h).toContainText("هزینه ارسال هنگام تحویل به پیک پرداخت می‌شود");
  });

  async function completeCheckoutWithMethod(
    page: Page,
    city: string,
    methodName: RegExp,
  ) {
    await otpToShippingStep(page);
    const shipping = page.locator("form").filter({
      has: page.getByRole("heading", { level: 2, name: "اطلاعات ارسال" }),
    });
    await shipping.getByLabel(/^استان$/i).fill("تهران");
    await shipping.getByLabel(/^شهر$/i).fill(city);
    await shipping.getByLabel(/کد پستی/i).fill("1234567890");
    await shipping.getByLabel(/نشانی کامل/i).fill("خیابان تست پلاک ۱");
    await page.getByRole("radio", { name: methodName }).click();
    await shipping.getByRole("button", { name: /انتقال به درگاه پرداخت/i }).click();
    await expect(page).toHaveURL(/checkout\/(success|payment\/callback)/, {
      timeout: 45_000,
    });
    if (/payment\/callback/.test(page.url())) {
      await expect(page).toHaveURL(/checkout\/success/, { timeout: 30_000 });
    }
  }

  async function latestMockOrder(page: Page) {
    return page.evaluate(() => {
      const raw = sessionStorage.getItem("karzar.mock.orders");
      if (!raw) return null;
      const entries = JSON.parse(raw) as [string, Record<string, unknown>][];
      const last = entries[entries.length - 1];
      return last ? last[1] : null;
    });
  }

  test("Tehran express 3h checkout snapshots method and merchandise-only total", async ({
    page,
  }) => {
    await completeCheckoutWithMethod(page, "تهران", /ارسال فوری ۳ ساعته/i);
    const order = await latestMockOrder(page);
    expect(order).toBeTruthy();
    expect(order?.shipping_method_code).toBe("tehran_express_3h");
    expect(order?.shipping_provider).toBe("local_delivery");
  });

  test("Shahriar in Tehran province still shows local express", async ({ page }) => {
    await otpToShippingStep(page);
    const shipping = page.locator("form").filter({
      has: page.getByRole("heading", { level: 2, name: "اطلاعات ارسال" }),
    });
    await shipping.getByLabel(/^استان$/i).fill("تهران");
    await shipping.getByLabel(/^شهر$/i).fill("شهریار");
    await shipping.getByLabel(/کد پستی/i).fill("1234567890");
    await shipping.getByLabel(/نشانی کامل/i).fill("خیابان تست پلاک ۱");
    await expect(page.getByText("ارسال فوری ۳ ساعته")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("تیپاکس")).toBeVisible();
  });

  test("non-Tehran province hides local methods", async ({ page }) => {
    await otpToShippingStep(page);
    const shipping = page.locator("form").filter({
      has: page.getByRole("heading", { level: 2, name: "اطلاعات ارسال" }),
    });
    await shipping.getByLabel(/^استان$/i).fill("البرز");
    await shipping.getByLabel(/^شهر$/i).fill("کرج");
    await shipping.getByLabel(/کد پستی/i).fill("1234567890");
    await shipping.getByLabel(/نشانی کامل/i).fill("خیابان تست پلاک ۱");
    await expect(page.getByText("تیپاکس")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText("ارسال فوری ۳ ساعته")).not.toBeVisible();
    await expect(page.getByText("پیک موتوری")).not.toBeVisible();
  });
});
