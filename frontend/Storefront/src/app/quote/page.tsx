import type { Metadata } from "next";
import { CartView } from "@/components/cart/cart-view";

export const metadata: Metadata = { title: "سبد استعلام" };

export default function QuotePage() {
  return <CartView mode="quote" />;
}
