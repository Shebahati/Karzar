import { Suspense } from "react";
import { PaymentCallbackView } from "@/components/checkout/payment-callback-view";

export default function PaymentCallbackPage() {
  return (
    <Suspense fallback={null}>
      <PaymentCallbackView />
    </Suspense>
  );
}
