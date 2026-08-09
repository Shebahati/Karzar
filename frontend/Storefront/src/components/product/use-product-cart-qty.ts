"use client";

import { useCartStore } from "@/store/cart-store";
import type { ProductDetail, ProductSummary } from "@/types/product";

export const CART_QTY_MAX = 99;

/** Normalize detail/summary into the shape the cart store persists. */
export function toCartProductSummary(
  product: ProductDetail | ProductSummary,
): ProductSummary {
  return {
    id: product.id,
    sku: product.sku,
    name: product.name,
    thumbnail: product.thumbnail,
    base_price: product.base_price,
    original_price: product.original_price,
    discount_percent: product.discount_percent,
    stock_status: product.stock_status,
    availability: product.availability,
    is_original: product.is_original,
    category: product.category,
    brand: product.brand,
  };
}

/**
 * Live cart quantity for one product — shared by product-card ATC,
 * PDP buy card, and mobile sticky buy bar.
 */
export function useProductCartQty(product: ProductSummary) {
  const qty = useCartStore(
    (s) => s.cart.find((l) => l.product.id === product.id)?.quantity ?? 0,
  );
  const addToCart = useCartStore((s) => s.addToCart);
  const setCartQuantity = useCartStore((s) => s.setCartQuantity);
  const removeFromCart = useCartStore((s) => s.removeFromCart);

  const addOne = () => {
    addToCart(product, 1);
  };

  const increment = () => {
    if (qty >= CART_QTY_MAX) return;
    addToCart(product, 1);
  };

  const decrement = () => {
    if (qty <= 0) return;
    if (qty <= 1) {
      removeFromCart(product.id);
      return;
    }
    setCartQuantity(product.id, qty - 1);
  };

  return {
    qty,
    inCart: qty > 0,
    addOne,
    increment,
    decrement,
    canIncrement: qty < CART_QTY_MAX,
  };
}

/** Live quote/inquiry quantity for price-less products. */
export function useProductQuoteQty(product: ProductSummary) {
  const qty = useCartStore(
    (s) => s.quote.find((l) => l.product.id === product.id)?.quantity ?? 0,
  );
  const addToQuote = useCartStore((s) => s.addToQuote);
  const setQuoteQuantity = useCartStore((s) => s.setQuoteQuantity);
  const removeFromQuote = useCartStore((s) => s.removeFromQuote);

  const addOne = () => {
    addToQuote(product, 1);
  };

  const increment = () => {
    if (qty >= CART_QTY_MAX) return;
    addToQuote(product, 1);
  };

  const decrement = () => {
    if (qty <= 0) return;
    if (qty <= 1) {
      removeFromQuote(product.id);
      return;
    }
    setQuoteQuantity(product.id, qty - 1);
  };

  return {
    qty,
    inQuote: qty > 0,
    addOne,
    increment,
    decrement,
    canIncrement: qty < CART_QTY_MAX,
  };
}
