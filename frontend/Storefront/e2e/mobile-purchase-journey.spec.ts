import { expect, test, type Page } from "@playwright/test";
import {
  MOBILE_HEIGHT,
  MOBILE_WIDTHS,
  addToCartFromPdp,
  assertCartLineQuantityIsOne,
  assertNoHorizontalOverflow,
  cartCheckoutCta,
  E2E_CATALOG_PRODUCT_NAME,
  fillPersianShippingForm,
  mockCheckoutSuccessWithRefresh,
  mockOtpLoginAtCheckout,
  mobilePayCta,
  openCartViaMobileUi,
  openPdpViaSearch,
  skipFirstVisitSplash,
} from "./helpers/storefront-e2e";

async function prepareMobile(page: Page, width: number) {
  await skipFirstVisitSplash(page);
  await page.setViewportSize({ width, height: MOBILE_HEIGHT });
  await page.goto("/", { waitUntil: "domcontentloaded", timeout: 120_000 });
}

test.describe("Mobile full purchase journey (#462)", () => {
  test.setTimeout(360_000);

  for (const width of MOBILE_WIDTHS) {
    test(`width ${width}: full mobile purchase journey`, async ({ page }) => {
      await prepareMobile(page, width);

      await openPdpViaSearch(page);
      await assertNoHorizontalOverflow(page);

      await addToCartFromPdp(page);

      await openCartViaMobileUi(page);
      await assertNoHorizontalOverflow(page);
      await assertCartLineQuantityIsOne(page, E2E_CATALOG_PRODUCT_NAME);

      const checkoutCta = cartCheckoutCta(page);
      await expect(checkoutCta).toBeVisible({ timeout: 20_000 });
      await expect(checkoutCta).toBeEnabled();
      await checkoutCta.click();
      await expect(page).toHaveURL(/\/checkout/, { timeout: 15_000 });
      await assertNoHorizontalOverflow(page);

      await expect(
        page.getByRole("heading", { level: 2, name: "ورود برای پرداخت" }),
      ).toBeVisible({ timeout: 20_000 });

      await mockOtpLoginAtCheckout(page);

      await fillPersianShippingForm(page);
      await assertNoHorizontalOverflow(page);

      const payCta = mobilePayCta(page);
      await expect(payCta).toBeVisible({ timeout: 15_000 });
      await expect(payCta).toBeEnabled({ timeout: 15_000 });
      await payCta.click();

      await mockCheckoutSuccessWithRefresh(page);
      await assertNoHorizontalOverflow(page);
    });
  }
});
