"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError } from "@/lib/api-client";
import { isQuoteExpired } from "@/lib/shipping-quote";
import { shippingService } from "@/services/shipping";
import { useCartStore } from "@/store/cart-store";
import type { ShippingCity, ShippingMethodOption, ShippingQuoteOption } from "@/types/shipping";

export function methodOptionSubtitle(code: string): string {
  if (code === "tehran_express") {
    return "هزینه ارسال هنگام تحویل به پیک پرداخت می‌شود";
  }
  if (code === "tipax_standard") {
    return "هزینه ارسال هنگام تحویل از گیرنده دریافت می‌شود";
  }
  if (code === "chapar_standard") {
    return "هزینه ارسال هنگام تحویل از گیرنده دریافت می‌شود";
  }
  return "پرداخت هزینه ارسال هنگام تحویل";
}

export function useCheckoutShipping(isPurchase: boolean) {
  const cart = useCartStore((s) => s.cart);
  const [enabled, setEnabled] = useState(false);
  const [statusLoaded, setStatusLoaded] = useState(false);
  const [methodSelectionEnabled, setMethodSelectionEnabled] = useState(false);
  const [checkoutQuoteRequired, setCheckoutQuoteRequired] = useState(false);
  const [shippingPaymentMode, setShippingPaymentMode] = useState<string | null>(null);
  const [cities, setCities] = useState<ShippingCity[]>([]);
  const [cityQuery, setCityQuery] = useState("");
  const [locationCode, setLocationCode] = useState<number | null>(null);
  const [options, setOptions] = useState<ShippingQuoteOption[]>([]);
  const [methodOptions, setMethodOptions] = useState<ShippingMethodOption[]>([]);
  const [selected, setSelected] = useState<ShippingQuoteOption | null>(null);
  const [selectedMethodCode, setSelectedMethodCode] = useState<string | null>(null);
  const [expiresAt, setExpiresAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [unavailable, setUnavailable] = useState(false);

  const receiverDue =
    shippingPaymentMode === "receiver_due" || methodSelectionEnabled;

  useEffect(() => {
    if (!isPurchase) return;
    let cancelled = false;
    void (async () => {
      try {
        const status = await shippingService.status();
        if (cancelled) return;
        setEnabled(status.enabled);
        setMethodSelectionEnabled(Boolean(status.method_selection_enabled));
        setCheckoutQuoteRequired(
          Boolean(
            status.checkout_quote_required ??
              (status.enabled &&
                !status.method_selection_enabled &&
                status.shipping_payment_mode !== "receiver_due"),
          ),
        );
        setShippingPaymentMode(status.shipping_payment_mode ?? null);
        setStatusLoaded(true);
        if (!status.enabled) return;
        if (!status.method_selection_enabled) {
          const rows = await shippingService.cities();
          if (!cancelled) setCities(rows);
        }
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

  const refreshMethodOptions = useCallback(
    async (province: string, city: string, postalCode?: string) => {
      if (!methodSelectionEnabled) return;
      const prov = province.trim();
      const c = city.trim();
      if (prov.length < 2 || c.length < 2) {
        setMethodOptions([]);
        setSelectedMethodCode(null);
        return;
      }
      setLoading(true);
      setError(null);
      setUnavailable(false);
      try {
        const rows = await shippingService.methodOptions({
          province: prov,
          city: c,
          postal_code: postalCode,
        });
        setMethodOptions(rows);
        setSelectedMethodCode((prev) =>
          prev && rows.some((r) => r.code === prev) ? prev : null,
        );
      } catch (err) {
        setMethodOptions([]);
        setSelectedMethodCode(null);
        setUnavailable(true);
        setError(
          err instanceof ApiError && err.message
            ? err.message
            : "بارگذاری روش‌های ارسال ناموفق بود.",
        );
      } finally {
        setLoading(false);
      }
    },
    [methodSelectionEnabled],
  );

  const refreshQuotes = useCallback(
    async (code: number, postalCode?: string, cityName?: string, provinceName?: string) => {
      if (!checkoutQuoteRequired) {
        setOptions([]);
        setSelected(null);
        setExpiresAt(null);
        setLoading(false);
        return;
      }
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
    [items, checkoutQuoteRequired],
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
    const list = q
      ? cities.filter((city) => city.name.includes(q) || (city.province_name ?? "").includes(q))
      : cities;
    return list.slice(0, 80);
  }, [cities, cityQuery]);

  return {
    enabled,
    statusLoaded,
    methodSelectionEnabled,
    checkoutQuoteRequired,
    shippingPaymentMode,
    receiverDue,
    cities,
    cityQuery,
    setCityQuery,
    filteredCities,
    locationCode,
    setLocationCode,
    options,
    methodOptions,
    selected,
    setSelected,
    selectedMethodCode,
    setSelectedMethodCode,
    expiresAt,
    loading,
    error,
    unavailable,
    refreshQuotes,
    refreshMethodOptions,
  };
}
