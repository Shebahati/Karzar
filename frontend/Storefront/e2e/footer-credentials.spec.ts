import { expect, test } from "@playwright/test";

const ENAMAD_TRUST_URL =
  "https://trustseal.enamad.ir/?id=6961566&Code=5F01NsyiqBFfBjNyzpNxr70bt4r065sr";

test.describe("footer credentials", () => {
  test("exposes a single Enamad verification card under مجوزها و اعتبارها", async ({
    page,
  }) => {
    await page.goto("/about", { waitUntil: "domcontentloaded", timeout: 120_000 });

    const footer = page.locator("footer");
    await expect(
      footer.getByRole("heading", { name: "مجوزها و اعتبارها" }),
    ).toBeVisible({ timeout: 20_000 });

    const enamad = footer.locator(`a[href="${ENAMAD_TRUST_URL}"]`);
    await expect(enamad).toHaveCount(1);
    await expect(enamad).toBeVisible();
    await expect(enamad).toHaveAttribute("rel", "noopener");
    await expect(enamad).toHaveAttribute("referrerpolicy", "origin");
    await expect(enamad).toHaveAttribute(
      "aria-label",
      "استعلام نماد اعتماد الکترونیکی کارزار",
    );

    await expect(footer.getByText("پروانه کسب مجازی")).toHaveCount(0);
    await expect(footer.getByText("پروانه کسب حضوری")).toHaveCount(0);
  });
});
