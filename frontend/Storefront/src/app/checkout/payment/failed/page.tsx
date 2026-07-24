import { Suspense } from "react";
import { PaymentFailedView } from "@/components/checkout/payment-failed-view";

export default function PaymentFailedPage() {
  return (
    <Suspense fallback={null}>
      <PaymentFailedView />
    </Suspense>
  );
}
