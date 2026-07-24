import { Suspense } from "react";
import type { Metadata } from "next";
import { CheckoutView } from "@/components/checkout/checkout-view";
import { Container } from "@/components/ui/container";

export const metadata: Metadata = { title: "تکمیل خرید" };

export default function CheckoutPage() {
  return (
    <Suspense fallback={<Container className="py-16" />}>
      <CheckoutView />
    </Suspense>
  );
}
