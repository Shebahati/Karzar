import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import {
  PURCHASE_PAUSED_MESSAGE,
  PurchasePausedNotice,
} from "@/components/commerce/purchase-paused-notice";

describe("PurchasePausedNotice", () => {
  it("explains the pause and keeps the inquiry path", () => {
    const html = renderToStaticMarkup(<PurchasePausedNotice />);
    expect(html).toContain(PURCHASE_PAUSED_MESSAGE);
    expect(html).toContain("سبد خرید شما حفظ می‌شود");
    expect(html).toContain('href="/quote"');
    expect(html).not.toContain("انتقال به درگاه");
    expect(html).not.toContain("تکمیل خرید و پرداخت");
  });

  it("prefers the server message when present", () => {
    const html = renderToStaticMarkup(
      <PurchasePausedNotice message="سفارش آنلاین تا اصلاح قیمت‌ها بسته است." />,
    );
    expect(html).toContain("سفارش آنلاین تا اصلاح قیمت‌ها بسته است.");
    expect(html).not.toContain(PURCHASE_PAUSED_MESSAGE);
  });
});
