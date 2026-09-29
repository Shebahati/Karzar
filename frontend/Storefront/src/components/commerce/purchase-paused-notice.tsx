import Link from "next/link";

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
      <Link href="/quote" className="mt-3 inline-block font-bold text-primary">
        ثبت درخواست استعلام
      </Link>
    </div>
  );
}
