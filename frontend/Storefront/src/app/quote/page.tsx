import type { Metadata } from "next";
import { CartView } from "@/components/cart/cart-view";
import { NOINDEX_NOFOLLOW } from "@/lib/crawl-hygiene";

export const metadata: Metadata = {
  title: "سبد استعلام",
  robots: NOINDEX_NOFOLLOW,
};

export default function QuotePage() {
  return <CartView mode="quote" />;
}
