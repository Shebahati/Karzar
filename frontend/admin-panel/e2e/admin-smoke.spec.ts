import { expect, test, type Page } from "@playwright/test";

const MOCK_PHONE = "09120000000";
const MOCK_PASSWORD = "Admin@123456";
const MOCK_PIN = "84729101";

/** Page h2 only — layout header also uses an h1 with the same title. */
const productsPageHeading = (page: Page) =>
  page.getByRole("heading", { level: 2, name: "مدیریت محصولات" });

async function fillLoginForm(page: Page) {
  const phone = page.locator("#phone");
  await expect(phone).toBeVisible({ timeout: 30_000 });
  await phone.fill(MOCK_PHONE);
  const password = page.locator("#password");
  if (await password.isVisible()) {
    await password.fill(MOCK_PASSWORD);
  }
  await page.getByRole("button", { name: /^ورود$/ }).click();
}

async function loginAsMockAdmin(page: Page) {
  await page.goto("/login");
  // CardTitle is h3 — avoid loose /ورود/ matching unrelated text.
  await expect(
    page.getByRole("heading", { level: 3, name: "ورود به پنل کارزار" }),
  ).toBeVisible({ timeout: 30_000 });
  await fillLoginForm(page);
  await page.waitForURL((url) => !url.pathname.startsWith("/login"), {
    timeout: 30_000,
  });
}

/**
 * Soft session cookie is set on login for middleware UX. Middleware / AuthGate
 * may still bounce to /login — complete login in-place so ?next= is preserved.
 */
async function gotoProductsWithSession(page: Page) {
  await page.goto("/catalog/products");

  const heading = productsPageHeading(page);
  const phone = page.locator("#phone");

  await expect(heading.or(phone)).toBeVisible({ timeout: 30_000 });

  if (await phone.isVisible().catch(() => false)) {
    await fillLoginForm(page);
  }

  await expect(heading).toBeVisible({ timeout: 30_000 });
}

/**
 * Smoke: admin mock login → products → step-up PIN dialog.
 */
test.describe("admin smoke (mock)", () => {
  test("login → products → step-up on delete", async ({ page }) => {
    await loginAsMockAdmin(page);
    await gotoProductsWithSession(page);

    const deleteBtn = page.getByRole("button", { name: /حذف محصول/i }).first();
    await expect(deleteBtn).toBeVisible({ timeout: 20_000 });
    await deleteBtn.click();

    const dialog = page.getByRole("dialog");
    await expect(
      dialog.getByRole("heading", { name: "حذف محصول" }),
    ).toBeVisible({ timeout: 10_000 });
    const pinInput = page.locator("#step-up-pin");
    await expect(pinInput).toBeVisible();
    await pinInput.fill(MOCK_PIN);
    await page.getByRole("button", { name: /تأیید و ادامه/ }).click();

    await expect(pinInput).toBeHidden({ timeout: 15_000 });
    await expect(productsPageHeading(page)).toBeVisible({ timeout: 15_000 });
  });
});
