"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError } from "@/lib/api-client";
import { isQuoteExpired } from "@/lib/shipping-quote";
import { shippingService } from "@/services/shipping";
import { useCartStore } from "@/store/cart-store";
import type { ShippingCity, ShippingQuoteOption } from "@/types/shipping";

export function useCheckoutShipping(isPurchase: boolean) {
  const cart = useCartStore((s) => s.cart);
  const [enabled, setEnabled] = useState(false);
  const [statusLoaded, setStatusLoaded] = useState(false);
  const [cities, setCities] = useState<ShippingCity[]>([]);
  const [cityQuery, setCityQuery] = useState("");
  const [locationCode, setLocationCode] = useState<number | null>(null);
  const [options, setOptions] = useState<ShippingQuoteOption[]>([]);
  const [selected, setSelected] = useState<ShippingQuoteOption | null>(null);
  const [expiresAt, setExpiresAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    if (!isPurchase) return;
    let cancelled = false;
    void (async () => {
      try {
        const status = await shippingService.status();
        if (cancelled) return;
        setEnabled(status.enabled);
        setStatusLoaded(true);
        if (!status.enabled) return;
        const rows = await shippingService.cities();
        if (!cancelled) setCities(rows);
      } catch {
        if (!cancelled) {
          setStatusLoaded(true);
          setUnavailable(true);
          setError("سرویس ارسال موقتاً در دسترس نیست. دوباره تلاش کنید.");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isPurchase]);

  const items = useMemo(
    () => cart.map((line) => ({ product_id: line.product.id, quantity: line.quantity })),
    [cart],
  );

  const refreshQuotes = useCallback(
    async (code: number, postalCode?: string, cityName?: string, provinceName?: string) => {
      setLoading(true);
      setError(null);
      setUnavailable(false);
      setSelected(null);
      try {
        const result = await shippingService.quotes({
          items,
          location_code: code,
          postal_code: postalCode,
          city_name: cityName,
          province_name: provinceName,
        });
        setOptions(result.options);
        setExpiresAt(result.expires_at);
      } catch (err) {
        setOptions([]);
        setExpiresAt(null);
        if (err instanceof ApiError && err.errorCode === "SHIPPING_DATA_INCOMPLETE") {
          setError("اطلاعات بسته‌بندی برخی کالاها ناقص است. لطفاً با فروشگاه تماس بگیرید.");
          setUnavailable(true);
          return;
        }
        if (err instanceof ApiError && err.errorCode === "SHIPPING_FREIGHT_REQUIRED") {
          setError("این سفارش نیاز به ارسال باربری/استعلام دارد و از مسیر خرید پستی قابل تکمیل نیست.");
          setUnavailable(true);
          return;
        }
        setUnavailable(true);
        setError(
          err instanceof ApiError && err.message
            ? err.message
            : "محاسبه هزینه ارسال ناموفق بود. دوباره تلاش کنید.",
        );
      } finally {
        setLoading(false);
      }
    },
    [items],
  );

  useEffect(() => {
    if (!expiresAt) return;
    const timer = window.setInterval(() => {
      if (isQuoteExpired(expiresAt)) {
        setSelected(null);
        setError("مهلت نرخ ارسال تمام شد. شهر را دوباره انتخاب کنید.");
      }
    }, 10000);
    return () => window.clearInterval(timer);
  }, [expiresAt]);

  const filteredCities = useMemo(() => {
    const q = cityQuery.trim();
    const list = q ? cities.filter((city) => city.name.includes(q) || (city.province_name ?? "").includes(q)) : cities;
    return list.slice(0, 80);
  }, [cities, cityQuery]);

  return {
    enabled,
    statusLoaded,
    cities,
    cityQuery,
    setCityQuery,
    filteredCities,
    locationCode,
    setLocationCode,
    options,
    selected,
    setSelected,
    expiresAt,
    loading,
    error,
    unavailable,
    refreshQuotes,
  };
}
