import type { Metadata } from "next";
import { Container } from "@/components/ui/container";

export const metadata: Metadata = {
  title: "قوانین استفاده",
  description: "شرایط و قوانین استفاده از فروشگاه اینترنتی کارزار.",
};

export default function TermsPage() {
  return (
    <Container className="py-10 lg:py-16">
      <h1 className="text-3xl font-bold text-foreground">قوانین استفاده</h1>
      <div className="mt-6 max-w-3xl space-y-4 text-sm leading-7 text-muted-foreground">
        <p>
          استفاده از وب‌سایت کارزار به‌معنای پذیرش این شرایط است. محتوای فروشگاه
          صرفاً جهت معرفی و فروش ابزارآلات صنعتی ارائه می‌شود.
        </p>
        <p>
          قیمت‌ها و موجودی ممکن است بدون اطلاع قبلی به‌روز شوند. سفارش پس از
          تأیید پرداخت و موجودی نهایی می‌شود.
        </p>
        <p>
          برای سوالات حقوقی یا همکاری با ما از طریق{" "}
          <a className="font-bold text-primary" href="mailto:info@karzartools.com">
            info@karzartools.com
          </a>{" "}
          در تماس باشید.
        </p>
      </div>
    </Container>
  );
}
