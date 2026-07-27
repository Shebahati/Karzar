import type { Metadata } from "next";
import { CartView } from "@/components/cart/cart-view";
import { NOINDEX_NOFOLLOW } from "@/lib/crawl-hygiene";

export const metadata: Metadata = {
  title: "سبد خرید",
  robots: NOINDEX_NOFOLLOW,
};

export default function CartPage() {
  return <CartView mode="cart" />;
}
