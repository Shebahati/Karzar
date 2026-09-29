import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import {
  PURCHASE_PAUSED_MESSAGE,
  PurchasePausedNotice,
} from "@/components/commerce/purchase-paused-notice";
import { STORE_PHONE_DISPLAY, STORE_PHONE_E164 } from "@/lib/store-location";

describe("PurchasePausedNotice", () => {
  it("explains the pause and offers inquiry plus a support call", () => {
    const html = renderToStaticMarkup(<PurchasePausedNotice />);
    expect(html).toContain(PURCHASE_PAUSED_MESSAGE);
    expect(html).toContain("سبد خرید شما حفظ می‌شود");
    expect(html).toContain('href="/quote"');
    expect(html).toContain("ثبت درخواست استعلام");
    expect(html).toContain(STORE_PHONE_DISPLAY);
    expect(html).toContain(`href="tel:${STORE_PHONE_E164}"`);
    expect(html).toContain("تماس با پشتیبانی");
    expect(html).not.toContain("انتقال به درگاه");
    expect(html).not.toContain("تکمیل خرید و پرداخت");
  });

  it("overrides only the main pause message when the server provides one", () => {
    const html = renderToStaticMarkup(
      <PurchasePausedNotice message="سفارش آنلاین تا اصلاح قیمت‌ها بسته است." />,
    );
    expect(html).toContain("سفارش آنلاین تا اصلاح قیمت‌ها بسته است.");
    expect(html).not.toContain(PURCHASE_PAUSED_MESSAGE);
    expect(html).toContain('href="/quote"');
    expect(html).toContain("ثبت درخواست استعلام");
    expect(html).toContain(STORE_PHONE_DISPLAY);
    expect(html).toContain(`href="tel:${STORE_PHONE_E164}"`);
    expect(html).toContain("تماس با پشتیبانی");
    expect(html).toContain("سبد خرید شما حفظ می‌شود");
    expect(html).not.toContain("انتقال به درگاه");
    expect(html).not.toContain("تکمیل خرید و پرداخت");
  });
});
