import { Suspense } from "react";
import type { Metadata } from "next";
import { SuccessView } from "@/components/checkout/success-view";
import { Container } from "@/components/ui/container";

export const metadata: Metadata = { title: "ثبت موفق سفارش" };

export default function CheckoutSuccessPage() {
  return (
    <Suspense fallback={<Container className="py-16" />}>
      <SuccessView />
    </Suspense>
  );
}
