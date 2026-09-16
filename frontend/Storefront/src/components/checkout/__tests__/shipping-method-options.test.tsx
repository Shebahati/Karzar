import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { ShippingMethodOptions } from "@/components/checkout/shipping-options";

const tehranProvinceOptions = [
  {
    code: "tipax_standard",
    title: "تیپاکس",
    payment_mode: "receiver_due",
    price: null,
    price_label: "پس‌کرایه",
  },
  {
    code: "chapar_standard",
    title: "چاپار",
    payment_mode: "receiver_due",
    price: null,
    price_label: "پس‌کرایه",
  },
  {
    code: "post_pishtaz",
    title: "پست پیشتاز",
    payment_mode: "receiver_due",
    price: null,
    price_label: "پس‌کرایه",
  },
  {
    code: "tehran_motorcycle_48h",
    title: "پیک موتوری حداکثر تا ۴۸ ساعت",
    payment_mode: "receiver_due",
    price: null,
    price_label: "پس‌کرایه",
  },
  {
    code: "tehran_express_3h",
    title: "ارسال فوری ۳ ساعته",
    payment_mode: "receiver_due",
    price: null,
    price_label: "پس‌کرایه",
  },
];

describe("ShippingMethodOptions", () => {
  it("renders receiver-due labels without free shipping", () => {
    const html = renderToStaticMarkup(
      <ShippingMethodOptions
        options={tehranProvinceOptions}
        selectedCode="tipax_standard"
        loading={false}
        error={null}
        onSelect={() => {}}
      />,
    );
    expect(html).toContain("تیپاکس");
    expect(html).toContain("پست پیشتاز");
    expect(html).toContain("ارسال فوری ۳ ساعته");
    expect(html).toContain("پس‌کرایه");
    expect(html).not.toContain("رایگان");
    expect(html).not.toContain("0 تومان");
    expect(html).toContain("هزینه ارسال هنگام تحویل از گیرنده دریافت می‌شود");
  });

  it("renders API error", () => {
    const html = renderToStaticMarkup(
      <ShippingMethodOptions
        options={[]}
        selectedCode={null}
        loading={false}
        error="خطای تست"
        onSelect={() => {}}
      />,
    );
    expect(html).toContain("خطای تست");
  });
});
