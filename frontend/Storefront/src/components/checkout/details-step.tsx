"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Document, Wallet } from "react-iconly";
import { Button } from "@/components/ui/button";
import { Field, fieldInputClass, fieldTextareaClass } from "@/components/ui/field";
import {
  inquirySchema,
  shippingSchema,
  type InquiryValues,
  type ShippingValues,
} from "@/lib/validation";
import { ShippingOptions } from "@/components/checkout/shipping-options";
import { useCheckoutShipping } from "@/features/checkout/use-checkout-shipping";
import { canSubmitPurchaseShipping } from "@/lib/shipping-quote";
import { isLoggedIn } from "@/lib/api-client";
import { cn, toPersianDigits } from "@/lib/utils";
import { useAddressStore, type SavedAddress } from "@/store/address-store";
import type { ResolvedCustomer } from "@/components/checkout/auth-step";
import type { ShippingQuoteOption } from "@/types/shipping";

export interface DetailsResult {
  full_name: string;
  phone: string;
  company_name?: string | null;
  note?: string | null;
  shipping?: {
    province: string;
    city: string;
    postal_code: string;
    address_line: string;
    location_code?: number | null;
  };
  shipping_quote_token?: string | null;
}

/**
 * Step 2 of checkout. Branches on `isInquiry`:
 * - purchase  → full shipping address, primary action "پرداخت".
 * - inquiry   → optional company name, primary action "ثبت استعلام قیمت".
 */
export function DetailsStep({
  isInquiry,
  customer,
  submitting,
  canPay = true,
  onSubmit,
  onBack,
  onQuoteChange,
  onShippingModeChange,
}: {
  isInquiry: boolean;
  customer: ResolvedCustomer | null;
  submitting: boolean;
  canPay?: boolean;
  onSubmit: (result: DetailsResult) => void;
  onBack: () => void;
  onQuoteChange?: (amountToman: number | null) => void;
  onShippingModeChange?: (mode: "prepaid" | "receiver_due" | "none") => void;
}) {
  if (isInquiry) {
    return (
      <InquiryForm
        customer={customer}
        submitting={submitting}
        onSubmit={onSubmit}
        onBack={onBack}
      />
    );
  }
  return (
    <ShippingForm
      customer={customer}
      submitting={submitting}
      canPay={canPay}
      onSubmit={onSubmit}
      onBack={onBack}
      onQuoteChange={onQuoteChange}
      onShippingModeChange={onShippingModeChange}
    />
  );
}

type AddressMode = "saved" | "new";

function sameShipping(
  a: Pick<SavedAddress, "full_name" | "phone" | "province" | "city" | "postal_code" | "address_line">,
  b: Pick<ShippingValues, "full_name" | "phone" | "province" | "city" | "postal_code" | "address_line">,
) {
  return (
    a.full_name.trim() === b.full_name.trim() &&
    a.phone.trim() === b.phone.trim() &&
    a.province.trim() === b.province.trim() &&
    a.city.trim() === b.city.trim() &&
    a.postal_code.trim() === b.postal_code.trim() &&
    a.address_line.trim() === b.address_line.trim()
  );
}

function ShippingForm({
  customer,
  submitting,
  canPay,
  onSubmit,
  onBack,
  onQuoteChange,
  onShippingModeChange,
}: {
  customer: ResolvedCustomer | null;
  submitting: boolean;
  canPay: boolean;
  onSubmit: (r: DetailsResult) => void;
  onBack: () => void;
  onQuoteChange?: (amountToman: number | null) => void;
  onShippingModeChange?: (mode: "prepaid" | "receiver_due" | "none") => void;
}) {
  const addresses = useAddressStore((s) => s.addresses);
  const getDefault = useAddressStore((s) => s.getDefault);
  const addAddress = useAddressStore((s) => s.addAddress);
  const shipping = useCheckoutShipping(true);
  // Match SSR (guest) until mount — avoids hydration mismatch on auth read.
  const [loggedIn, setLoggedIn] = useState(false);
  useEffect(() => {
    setLoggedIn(isLoggedIn());
  }, []);
  const canUseSaved = loggedIn && addresses.length > 0;

  const [mode, setMode] = useState<AddressMode>(canUseSaved ? "saved" : "new");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    if (!canUseSaved) {
      setMode("new");
      return;
    }
    const def = getDefault();
    setSelectedId(def?.id ?? addresses[0]?.id ?? null);
    setMode("saved");
  }, [canUseSaved, addresses, getDefault]);

  const form = useForm<ShippingValues>({
    resolver: zodResolver(shippingSchema),
    defaultValues: {
      full_name: customer?.full_name ?? "",
      phone: customer?.phone ?? "",
    },
  });
  const { errors } = form.formState;
  const formId = "checkout-shipping-form";
  const watchedPostal = form.watch("postal_code");

  useEffect(() => {
    if (!shipping.enabled || shipping.locationCode == null) return;
    if (!shipping.checkoutQuoteRequired) return;
    const timer = window.setTimeout(() => {
      void shipping.refreshQuotes(
        shipping.locationCode as number,
        watchedPostal,
        form.getValues("city"),
        form.getValues("province"),
      );
    }, 400);
    return () => window.clearTimeout(timer);
    // Re-bind quote to the current postal code; client amounts are never authority.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [watchedPostal, shipping.locationCode, shipping.enabled, shipping.checkoutQuoteRequired]);

  useEffect(() => {
    if (!shipping.enabled) {
      onShippingModeChange?.("none");
      return;
    }
    onShippingModeChange?.(shipping.receiverDue ? "receiver_due" : "prepaid");
  }, [onShippingModeChange, shipping.enabled, shipping.receiverDue]);

  const applySaved = (addr: SavedAddress) => {
    form.reset({
      full_name: addr.full_name,
      phone: addr.phone,
      province: addr.province,
      city: addr.city,
      postal_code: addr.postal_code,
      address_line: addr.address_line,
      note: form.getValues("note") ?? "",
    });
  };

  useEffect(() => {
    if (mode !== "saved" || !selectedId) return;
    const addr = addresses.find((a) => a.id === selectedId);
    if (addr) applySaved(addr);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, selectedId]);

  const persistNewAddress = (v: ShippingValues) => {
    if (!loggedIn) return;
    if (mode === "saved") return;
    if (addresses.some((a) => sameShipping(a, v))) return;
    addAddress({
      label: v.city.trim() || "آدرس ارسال",
      full_name: v.full_name,
      phone: v.phone,
      province: v.province,
      city: v.city,
      postal_code: v.postal_code,
      address_line: v.address_line,
      is_default: addresses.length === 0,
    });
  };

  const handleShippingSubmit = (v: ShippingValues) => {
    if (
      shipping.enabled &&
      !canSubmitPurchaseShipping({
        postexEnabled: true,
        quoteToken: shipping.selected?.quote_token ?? null,
        expiresAt: shipping.expiresAt,
        shippingUnavailable: shipping.unavailable,
        checkoutQuoteRequired: shipping.checkoutQuoteRequired,
        locationCode: shipping.locationCode,
      })
    ) {
      return;
    }
    persistNewAddress(v);
    onSubmit({
      full_name: v.full_name,
      phone: v.phone,
      note: v.note || null,
      shipping: {
        province: v.province,
        city: v.city,
        postal_code: v.postal_code,
        address_line: v.address_line,
        location_code: shipping.locationCode,
      },
      shipping_quote_token: shipping.checkoutQuoteRequired
        ? (shipping.selected?.quote_token ?? null)
        : null,
    });
  };

  useEffect(() => {
    if (shipping.receiverDue) {
      onQuoteChange?.(null);
      return;
    }
    onQuoteChange?.(
      shipping.selected ? Number(shipping.selected.amount_toman) : null,
    );
  }, [onQuoteChange, shipping.selected, shipping.receiverDue]);

  const shippingReady =
    !shipping.enabled ||
    canSubmitPurchaseShipping({
      postexEnabled: true,
      quoteToken: shipping.selected?.quote_token ?? null,
      expiresAt: shipping.expiresAt,
      shippingUnavailable: shipping.unavailable,
      checkoutQuoteRequired: shipping.checkoutQuoteRequired,
      locationCode: shipping.locationCode,
    });

  return (
    <>
      <form
        id={formId}
        onSubmit={form.handleSubmit(handleShippingSubmit)}
        className="rounded-2xl bg-card p-6 shadow-soft sm:p-8"
      >
        <h2 className="text-lg font-bold text-foreground">اطلاعات ارسال</h2>
        {loggedIn && !canUseSaved && (
          <p className="mt-2 text-sm text-steel">
            این آدرس پس از ثبت سفارش در «آدرس‌های من» ذخیره می‌شود.
          </p>
        )}

        {canUseSaved && (
          <div className="mt-5 space-y-3">
            <p className="text-sm text-steel">
              یکی از آدرس‌های ذخیره‌شده را انتخاب کنید یا آدرس جدید وارد کنید.
            </p>
            <div
              role="tablist"
              aria-label="منبع آدرس"
              className="flex gap-2 rounded-xl bg-secondary p-1"
            >
              <button
                type="button"
                role="tab"
                aria-selected={mode === "saved"}
                onClick={() => setMode("saved")}
                className={cn(
                  "flex-1 rounded-lg px-3 py-2.5 text-sm font-bold transition-colors",
                  mode === "saved"
                    ? "bg-card text-foreground shadow-soft"
                    : "text-steel hover:text-foreground",
                )}
              >
                آدرس ذخیره‌شده
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={mode === "new"}
                onClick={() => {
                  setMode("new");
                  form.reset({
                    full_name: customer?.full_name ?? form.getValues("full_name") ?? "",
                    phone: customer?.phone ?? form.getValues("phone") ?? "",
                    province: "",
                    city: "",
                    postal_code: "",
                    address_line: "",
                    note: form.getValues("note") ?? "",
                  });
                }}
                className={cn(
                  "flex-1 rounded-lg px-3 py-2.5 text-sm font-bold transition-colors",
                  mode === "new"
                    ? "bg-card text-foreground shadow-soft"
                    : "text-steel hover:text-foreground",
                )}
              >
                آدرس جدید
              </button>
            </div>

            {mode === "saved" && (
              <div className="space-y-2" role="radiogroup" aria-label="انتخاب آدرس">
                {addresses.map((addr) => {
                  const active = selectedId === addr.id;
                  return (
                    <button
                      key={addr.id}
                      type="button"
                      role="radio"
                      aria-checked={active}
                      onClick={() => {
                        setSelectedId(addr.id);
                        applySaved(addr);
                      }}
                      className={cn(
                        "w-full rounded-xl border px-4 py-3 text-start transition-colors",
                        active
                          ? "border-primary/40 bg-accent"
                          : "border-border/50 bg-background hover:border-steel/30",
                      )}
                    >
                      <span className="flex items-center gap-2">
                        <span className="font-bold text-foreground">{addr.label}</span>
                        {addr.is_default && (
                          <span className="rounded-md bg-primary/10 px-1.5 py-0.5 text-[10px] font-bold text-primary">
                            پیش‌فرض
                          </span>
                        )}
                      </span>
                      <span className="mt-1 block text-xs leading-5 text-steel">
                        {addr.full_name} · {toPersianDigits(addr.phone)}
                        <br />
                        {addr.province}، {addr.city} — {addr.address_line}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        )}

        <div
          className={cn(
            "mt-6 grid gap-4 sm:grid-cols-2",
            mode === "saved" && canUseSaved ? "opacity-90" : "",
          )}
        >
          <Field label="نام و نام خانوادگی" error={errors.full_name?.message}>
            <input
              {...form.register("full_name")}
              className={fieldInputClass}
              readOnly={mode === "saved" && canUseSaved}
            />
          </Field>
          <Field label="شماره موبایل" error={errors.phone?.message}>
            <input
              {...form.register("phone")}
              inputMode="tel"
              className={`${fieldInputClass} tnum`}
              readOnly={mode === "saved" && canUseSaved}
            />
          </Field>
          <Field label="استان" error={errors.province?.message}>
            <input
              {...form.register("province")}
              className={fieldInputClass}
              readOnly={mode === "saved" && canUseSaved}
            />
          </Field>
          <Field label="شهر" error={errors.city?.message}>
            <input
              {...form.register("city")}
              className={fieldInputClass}
              readOnly={mode === "saved" && canUseSaved}
            />
          </Field>
          <Field label="کد پستی" error={errors.postal_code?.message}>
            <input
              {...form.register("postal_code")}
              inputMode="numeric"
              className={`${fieldInputClass} tnum`}
              readOnly={mode === "saved" && canUseSaved}
            />
          </Field>
          <Field label="نشانی کامل" error={errors.address_line?.message} className="sm:col-span-2">
            <textarea
              {...form.register("address_line")}
              rows={3}
              className={fieldTextareaClass}
              placeholder="خیابان، کوچه، پلاک، واحد"
              readOnly={mode === "saved" && canUseSaved}
            />
          </Field>
          {shipping.enabled && (
            <div className="sm:col-span-2 space-y-3 rounded-xl border border-border/60 bg-secondary/40 p-4">
              <h3 className="text-sm font-bold text-foreground">روش ارسال</h3>
              {shipping.receiverDue && (
                <p className="text-sm leading-6 text-foreground">
                  هزینه ارسال به‌صورت پس‌کرایه و هنگام تحویل از گیرنده دریافت می‌شود.
                </p>
              )}
              <Field label="شهر مقصد (کد شهر)">
                <input
                  value={shipping.cityQuery}
                  onChange={(event) => shipping.setCityQuery(event.target.value)}
                  className={fieldInputClass}
                  placeholder="جستجوی شهر"
                  autoComplete="off"
                />
              </Field>
              <div className="max-h-40 overflow-y-auto space-y-1" role="listbox" aria-label="شهرهای ارسال">
                {shipping.filteredCities.map((city) => {
                  const active = shipping.locationCode === city.code;
                  return (
                    <button
                      key={city.code}
                      type="button"
                      role="option"
                      aria-selected={active}
                      className={cn(
                        "w-full rounded-lg px-3 py-2 text-start text-sm",
                        active ? "bg-accent text-foreground" : "hover:bg-card",
                      )}
                      onClick={() => {
                        shipping.setLocationCode(city.code);
                        form.setValue("city", city.name);
                        if (city.province_name) form.setValue("province", city.province_name);
                        if (shipping.checkoutQuoteRequired) {
                          void shipping.refreshQuotes(
                            city.code,
                            form.getValues("postal_code"),
                            city.name,
                            city.province_name ?? form.getValues("province"),
                          );
                        }
                      }}
                    >
                      {city.name}
                      {city.province_name ? ` — ${city.province_name}` : ""}
                    </button>
                  );
                })}
              </div>
              {shipping.checkoutQuoteRequired ? (
                <ShippingOptions
                  options={shipping.options}
                  selectedToken={shipping.selected?.quote_token ?? null}
                  loading={shipping.loading}
                  error={shipping.error}
                  onSelect={(option: ShippingQuoteOption) => shipping.setSelected(option)}
                />
              ) : (
                <p className="text-xs text-steel">
                  مبلغ پرداخت اینترنتی فقط شامل محصولات و مالیات است؛ پس‌کرایه ارسال جداگانه از گیرنده
                  دریافت می‌شود.
                </p>
              )}
            </div>
          )}
          <Field label="توضیحات (اختیاری)" className="sm:col-span-2">
            <textarea {...form.register("note")} rows={2} className={fieldTextareaClass} />
          </Field>
        </div>

        <div className="mt-6 hidden gap-2 lg:flex">
          <Button type="submit" size="lg" className="flex-1 gap-2" disabled={submitting || !canPay || !shippingReady}>
            <Wallet set="bold" />
            {submitting ? "در حال ثبت…" : "انتقال به درگاه پرداخت"}
          </Button>
          <Button type="button" variant="muted" size="lg" onClick={onBack}>
            بازگشت
          </Button>
        </div>
        {!canPay && (
          <p className="mt-3 text-sm text-destructive" role="alert">
            برای پرداخت آنلاین ابتدا با کد یک‌بارمصرف وارد شوید.
          </p>
        )}
        {shipping.enabled && !shippingReady && (
          <p className="mt-3 text-sm text-destructive" role="alert">
            {shipping.receiverDue
              ? "برای ادامه خرید ابتدا شهر مقصد را انتخاب کنید."
              : "برای ادامه خرید ابتدا شهر مقصد و سرویس ارسال را انتخاب کنید."}
          </p>
        )}
      </form>

      {/* lg:hidden must be a utility — class `flex` would otherwise beat
          `.mobile-dock { @apply lg:hidden }` (components layer loses to utilities). */}
      <div className="mobile-dock flex gap-2 px-4 py-3 lg:hidden">
        <Button
          type="submit"
          form={formId}
          size="lg"
          className="flex-1 gap-2"
          disabled={submitting || !canPay || !shippingReady}
        >
          <Wallet set="bold" />
          {submitting ? "در حال ثبت…" : "پرداخت"}
        </Button>
        <Button type="button" variant="muted" size="lg" onClick={onBack}>
          بازگشت
        </Button>
      </div>
    </>
  );
}

function InquiryForm({
  customer,
  submitting,
  onSubmit,
  onBack,
}: {
  customer: ResolvedCustomer | null;
  submitting: boolean;
  onSubmit: (r: DetailsResult) => void;
  onBack: () => void;
}) {
  const form = useForm<InquiryValues>({
    resolver: zodResolver(inquirySchema),
    defaultValues: {
      full_name: customer?.full_name ?? "",
      phone: customer?.phone ?? "",
    },
  });
  const { errors } = form.formState;
  const formId = "checkout-inquiry-form";

  return (
    <>
      <form
        id={formId}
        onSubmit={form.handleSubmit((v) =>
          onSubmit({
            full_name: v.full_name,
            phone: v.phone,
            company_name: v.company_name || null,
            note: v.note || null,
          }),
        )}
        className="rounded-2xl bg-card p-6 shadow-soft sm:p-8"
      >
        <h2 className="text-lg font-bold text-foreground">اطلاعات استعلام</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          کارشناسان ما پس از بررسی، پیش‌فاکتور را برای شما ارسال می‌کنند.
        </p>
        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          <Field label="نام و نام خانوادگی" error={errors.full_name?.message}>
            <input {...form.register("full_name")} className={fieldInputClass} />
          </Field>
          <Field label="شماره موبایل" error={errors.phone?.message}>
            <input {...form.register("phone")} inputMode="tel" className={`${fieldInputClass} tnum`} />
          </Field>
          <Field
            label="نام شرکت (اختیاری)"
            hint="برای خریدهای سازمانی و صدور فاکتور رسمی"
            className="sm:col-span-2"
          >
            <input {...form.register("company_name")} className={fieldInputClass} />
          </Field>
          <Field label="توضیحات درخواست (اختیاری)" className="sm:col-span-2">
            <textarea
              {...form.register("note")}
              rows={3}
              className={fieldTextareaClass}
              placeholder="تعداد مورد نیاز، زمان تحویل، یا توضیحات فنی"
            />
          </Field>
        </div>

        <div className="mt-6 hidden gap-2 lg:flex">
          <Button type="submit" size="lg" className="flex-1 gap-2" disabled={submitting}>
            <Document set="bold" />
            {submitting ? "در حال ثبت…" : "ثبت استعلام قیمت"}
          </Button>
          <Button type="button" variant="muted" size="lg" onClick={onBack}>
            بازگشت
          </Button>
        </div>
      </form>

      <div className="mobile-dock flex gap-2 px-4 py-3 lg:hidden">
        <Button type="submit" form={formId} size="lg" className="flex-1 gap-2" disabled={submitting}>
          <Document set="bold" />
          {submitting ? "در حال ثبت…" : "ثبت استعلام"}
        </Button>
        <Button type="button" variant="muted" size="lg" onClick={onBack}>
          بازگشت
        </Button>
      </div>
    </>
  );
}
