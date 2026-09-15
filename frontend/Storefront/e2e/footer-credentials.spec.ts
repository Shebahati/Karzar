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
    const box = await enamad.boundingBox();
    expect(box).not.toBeNull();
    expect(box?.width ?? 0).toBeGreaterThanOrEqual(90);
    expect(box?.height ?? 0).toBeGreaterThanOrEqual(105);
    await expect(enamad).toHaveAttribute("rel", "noopener");
    await expect(enamad).toHaveAttribute("referrerpolicy", "origin");
    await expect(enamad).toHaveAttribute(
      "aria-label",
      "استعلام نماد اعتماد الکترونیکی کارزار",
    );

    await expect(footer.getByText("پروانه کسب مجازی")).toHaveCount(0);
    await expect(footer.getByText("پروانه کسب حضوری")).toHaveCount(0);
  });

  test("keeps credential cards readable at 320px without horizontal overflow", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 320, height: 800 });
    await page.goto("/about", { waitUntil: "domcontentloaded", timeout: 120_000 });

    const footer = page.locator("footer");
    const enamad = footer.locator(`a[href="${ENAMAD_TRUST_URL}"]`);
    await enamad.scrollIntoViewIfNeeded();
    await expect(enamad).toBeVisible({ timeout: 20_000 });

    const box = await enamad.boundingBox();
    expect(box?.width ?? 0).toBeGreaterThanOrEqual(90);
    expect(box?.height ?? 0).toBeGreaterThanOrEqual(105);

    const overflowX = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    );
    expect(overflowX).toBe(false);
  });
});
