import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { ShippingMethodOptions } from "@/components/checkout/shipping-options";

const tehranOptions = [
  {
    code: "tehran_express",
    title: "ارسال فوری تهران",
    payment_mode: "receiver_due",
    price: null,
    price_label: "پس‌کرایه",
  },
  {
    code: "tipax_standard",
    title: "تیپاکس",
    payment_mode: "receiver_due",
    price: null,
    price_label: "پس‌کرایه",
  },
];

describe("ShippingMethodOptions", () => {
  it("renders Tehran Express and receiver-due labels without free shipping", () => {
    const html = renderToStaticMarkup(
      <ShippingMethodOptions
        options={tehranOptions}
        selectedCode="tipax_standard"
        loading={false}
        error={null}
        onSelect={() => {}}
      />,
    );
    expect(html).toContain("ارسال فوری تهران");
    expect(html).toContain("تیپاکس");
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
