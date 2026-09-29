import Link from "next/link";
import { STORE_PHONE_DISPLAY, STORE_PHONE_E164 } from "@/lib/store-location";

/** Same copy as the API kill switch (`PURCHASE_CHECKOUT_DISABLED_MESSAGE`). */
export const PURCHASE_PAUSED_MESSAGE =
  "خرید آنلاین موقتاً در حال به‌روزرسانی است. لطفاً کمی بعد دوباره تلاش کنید یا درخواست استعلام ثبت کنید.";

export function PurchasePausedNotice({ message }: { message?: string | null }) {
  return (
    <div
      role="status"
      className="rounded-2xl bg-amber-500/10 p-4 text-sm leading-7 text-foreground ring-1 ring-inset ring-amber-600/20"
    >
      <p className="font-bold">سفارش آنلاین موقتاً متوقف است</p>
      <p className="mt-1">{message?.trim() || PURCHASE_PAUSED_MESSAGE}</p>
      <p className="mt-2 text-[#5E5F5E]">سبد خرید شما حفظ می‌شود. درخواست استعلام همچنان باز است.</p>
      <p className="mt-2">
        برای استعلام قیمت می‌توانید از طریق سایت درخواست استعلام ثبت کنید یا با پشتیبانی کارزار به
        شماره{" "}
        <span dir="ltr" className="inline-block tabular-nums tracking-wide">
          {STORE_PHONE_DISPLAY}
        </span>{" "}
        تماس بگیرید.
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2">
        <Link href="/quote" className="font-bold text-primary">
          ثبت درخواست استعلام
        </Link>
        <a
          href={`tel:${STORE_PHONE_E164}`}
          className="font-medium text-[#5E5F5E] underline-offset-4 hover:text-primary hover:underline"
        >
          تماس با پشتیبانی
        </a>
      </div>
    </div>
  );
}
