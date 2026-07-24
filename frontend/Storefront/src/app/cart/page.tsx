import type { Metadata } from "next";
import { CartView } from "@/components/cart/cart-view";

export const metadata: Metadata = { title: "سبد خرید" };

export default function CartPage() {
  return <CartView mode="cart" />;
}
