import type { Metadata } from "next";
import { Container } from "@/components/ui/container";

export const metadata: Metadata = {
  title: "حریم خصوصی",
  description: "سیاست حفظ حریم خصوصی کاربران فروشگاه کارزار.",
};

export default function PrivacyPage() {
  return (
    <Container className="py-10 lg:py-16">
      <h1 className="text-3xl font-bold text-foreground">حریم خصوصی</h1>
      <div className="mt-6 max-w-3xl space-y-4 text-sm leading-7 text-muted-foreground">
        <p>
          کارزار اطلاعات تماس و سفارش شما را صرفاً برای پردازش خرید، پشتیبانی و
          الزامات قانونی نگهداری می‌کند و به اشخاص ثالث غیرمرتبط نمی‌فروشد.
        </p>
        <p>
          داده‌های پرداخت از طریق درگاه معتبر پردازش می‌شود؛ کارزار شماره کارت
          کامل شما را ذخیره نمی‌کند.
        </p>
        <p>
          برای درخواست حذف یا اصلاح اطلاعات با{" "}
          <a className="font-bold text-primary" href="mailto:info@karzartools.com">
            info@karzartools.com
          </a>{" "}
          مکاتبه کنید.
        </p>
      </div>
    </Container>
  );
}
