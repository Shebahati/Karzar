import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const PAGES = ["/", "/catalog", "/checkout"] as const;

for (const path of PAGES) {
  test(`a11y smoke: ${path}`, async ({ page }) => {
    await page.goto(path);
    await page.waitForLoadState("networkidle");

    const results = await new AxeBuilder({ page })
      .disableRules(["color-contrast"])
      .analyze();

    const critical = results.violations.filter((v) => v.impact === "critical");
    expect(critical, JSON.stringify(critical, null, 2)).toEqual([]);
  });
}
