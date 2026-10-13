import Link from "next/link";

/** Compact legal notice beside purchase checkout submit (Refs #251 / #262). */
export function CheckoutPolicyNotice({ className }: { className?: string }) {
  return (
    <p className={className ?? "mt-3 text-xs leading-6 text-muted-foreground"}>
      ثبت سفارش و پرداخت تابع{" "}
      <Link href="/terms" className="font-bold text-foreground underline-offset-2 hover:text-primary hover:underline">
        قوانین استفاده
      </Link>{" "}
      و{" "}
      <Link href="/privacy" className="font-bold text-foreground underline-offset-2 hover:text-primary hover:underline">
        سیاست حریم خصوصی
      </Link>{" "}
      کارزار است.
    </p>
  );
}
