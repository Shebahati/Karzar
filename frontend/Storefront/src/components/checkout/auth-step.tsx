"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { Login, Message, User } from "react-iconly";
import { Button } from "@/components/ui/button";
import { authService } from "@/services/auth";
import { catalogService } from "@/services/catalog";
import {
  clearPendingInquiry,
  getPendingInquiry,
  pendingInquiryToCartLines,
} from "@/lib/inquiry-pending";
import { useCartStore } from "@/store/cart-store";
import { guestSchema, phoneSchema, type GuestValues } from "@/lib/validation";
import { toEnglishDigits } from "@/lib/utils";
import { z } from "zod";

export interface ResolvedCustomer {
  full_name: string;
  phone: string;
  is_guest: boolean;
}

type Lane = "choose" | "guest" | "otp";
const codeSchema = z.object({ code: z.string().length(5, "کد ۵ رقمی را کامل وارد کنید.") });

/**
 * Step 1 of checkout. For purchase mode (C2), guest checkout is disabled —
 * only OTP login is allowed. Inquiry mode still supports guest checkout.
 */
export function AuthStep({
  isInquiry = false,
  onResolved,
}: {
  isInquiry?: boolean;
  onResolved: (c: ResolvedCustomer) => void;
}) {
  const [lane, setLane] = useState<Lane>(isInquiry ? "choose" : "otp");
  const [phone, setPhone] = useState("");

  const guestForm = useForm<GuestValues>({ resolver: zodResolver(guestSchema) });

  const requestOtp = useMutation({
    mutationFn: (p: string) => authService.requestOtp({ phone: toEnglishDigits(p) }),
    onSuccess: () => setLane("otp"),
  });

  const codeForm = useForm<{ code: string }>({ resolver: zodResolver(codeSchema) });
  const [cartSyncError, setCartSyncError] = useState<string | null>(null);
  const verifyOtp = useMutation({
    mutationFn: (code: string) =>
      authService.verifyOtp({ phone: toEnglishDigits(phone), code }),
    onSuccess: async (result) => {
      const normalizedPhone = toEnglishDigits(phone);
      if (result.cart_sync_error) {
        setCartSyncError(result.cart_sync_error);
      } else {
        setCartSyncError(null);
      }
      try {
        const pending = getPendingInquiry(normalizedPhone);
        if (pending) {
          const products = await catalogService.getProductsByIds(
            pending.lines.map((l) => l.product_id),
          );
          const restored = pendingInquiryToCartLines(pending, products);
          if (restored.length) {
            useCartStore.getState().restoreQuote(restored);
            sessionStorage.setItem("karzar.inquiry.restored", "1");
          }
          clearPendingInquiry(normalizedPhone);
        }
      } catch {
        /* restore is best-effort */
      }

      window.dispatchEvent(new Event("karzar-auth-change"));

      try {
        const me = await authService.getMe();
        onResolved({
          full_name: me.full_name ?? "",
          phone: me.phone,
          is_guest: false,
        });
      } catch {
        onResolved({ full_name: "", phone: normalizedPhone, is_guest: false });
      }
    },
  });

  useEffect(() => {
    if (!isInquiry) setLane("otp");
  }, [isInquiry]);

  return (
    <div className="rounded-2xl bg-card p-6 shadow-soft sm:p-8">
      <h2 className="text-lg font-bold text-foreground">
        {isInquiry ? "ورود / ادامه خرید" : "ورود برای پرداخت"}
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">
        {isInquiry
          ? "برای ادامه می‌توانید وارد شوید یا به‌صورت مهمان ادامه دهید."
          : "پرداخت آنلاین فقط برای کاربران واردشده امکان‌پذیر است. لطفاً با کد یک‌بارمصرف وارد شوید."}
      </p>

      {cartSyncError && (
        <div
          role="alert"
          className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
        >
          {cartSyncError}
        </div>
      )}

      {lane === "choose" && isInquiry && (
        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          <button
            type="button"
            onClick={() => setLane("otp")}
            className="group flex flex-col items-start gap-2 rounded-2xl bg-secondary p-5 text-start transition-shadow hover:shadow-card"
          >
            <span className="grid h-11 w-11 place-items-center rounded-xl bg-primary text-primary-foreground shadow-primary-glow">
              <Login set="bold" />
            </span>
            <span className="mt-2 font-bold text-foreground">ورود با کد یک‌بارمصرف</span>
            <span className="text-xs text-muted-foreground">
              درخواست کد و ورود به حساب
            </span>
          </button>

          <button
            type="button"
            onClick={() => setLane("guest")}
            className="group flex flex-col items-start gap-2 rounded-2xl bg-secondary p-5 text-start transition-shadow hover:shadow-card"
          >
            <span className="grid h-11 w-11 place-items-center rounded-xl bg-foreground/85 text-white shadow-soft">
              <User set="bold" />
            </span>
            <span className="mt-2 font-bold text-foreground">ادامه به‌صورت مهمان</span>
            <span className="text-xs text-muted-foreground">
              فقط با نام و شماره موبایل
            </span>
          </button>
        </div>
      )}

      {lane === "guest" && isInquiry && (
        <form
          onSubmit={guestForm.handleSubmit((v) =>
            onResolved({
              full_name: v.full_name,
              phone: toEnglishDigits(v.phone),
              is_guest: true,
            }),
          )}
          className="mt-6 space-y-4"
        >
          <Field label="نام و نام خانوادگی" error={guestForm.formState.errors.full_name?.message}>
            <input
              {...guestForm.register("full_name")}
              className="h-12 w-full rounded-xl bg-input px-4 text-sm outline-none focus:ring-2 focus:ring-ring/40"
              placeholder="مثال: رضا محمدی"
            />
          </Field>
          <Field label="شماره موبایل" error={guestForm.formState.errors.phone?.message}>
            <input
              {...guestForm.register("phone")}
              inputMode="tel"
              className="h-12 w-full rounded-xl bg-input px-4 text-sm outline-none focus:ring-2 focus:ring-ring/40 tnum"
              placeholder="۰۹XXXXXXXXX"
            />
          </Field>
          <div className="flex gap-2">
            <Button type="submit" size="lg" className="flex-1">
              ادامه
            </Button>
            <Button type="button" variant="muted" size="lg" onClick={() => setLane("choose")}>
              بازگشت
            </Button>
          </div>
        </form>
      )}

      {lane === "otp" && (
        <OtpLane
          phone={phone}
          setPhone={setPhone}
          requestPending={requestOtp.isPending}
          verifyPending={verifyOtp.isPending}
          verifyError={verifyOtp.isError}
          codeForm={codeForm}
          onRequest={() => {
            const parsed = phoneSchema.safeParse(phone);
            if (parsed.success) requestOtp.mutate(phone);
          }}
          onVerify={(code) => verifyOtp.mutate(code)}
          sent={requestOtp.isSuccess}
          onBack={() => (isInquiry ? setLane("choose") : undefined)}
          showBack={isInquiry}
        />
      )}
    </div>
  );
}

function OtpLane({
  phone,
  setPhone,
  requestPending,
  verifyPending,
  verifyError,
  codeForm,
  onRequest,
  onVerify,
  sent,
  onBack,
  showBack = true,
}: {
  phone: string;
  setPhone: (v: string) => void;
  requestPending: boolean;
  verifyPending: boolean;
  verifyError: boolean;
  codeForm: ReturnType<typeof useForm<{ code: string }>>;
  onRequest: () => void;
  onVerify: (code: string) => void;
  sent: boolean;
  onBack?: () => void;
  showBack?: boolean;
}) {
  const phoneValid = /^09\d{9}$/.test(toEnglishDigits(phone));
  return (
    <div className="mt-6 space-y-4">
      {!sent ? (
        <>
          <Field label="شماره موبایل">
            <div className="relative">
              <span className="pointer-events-none absolute start-4 top-1/2 -translate-y-1/2 text-muted-foreground">
                <Message size="small" set="light" />
              </span>
              <input
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                inputMode="tel"
                autoFocus
                className="h-12 w-full rounded-xl bg-input ps-11 pe-4 text-sm outline-none focus:ring-2 focus:ring-ring/40 tnum"
                placeholder="۰۹XXXXXXXXX"
              />
            </div>
          </Field>
          <div className="flex gap-2">
            <Button
              type="button"
              size="lg"
              className="flex-1"
              disabled={!phoneValid || requestPending}
              onClick={onRequest}
            >
              {requestPending ? "در حال ارسال…" : "دریافت کد"}
            </Button>
            {showBack && onBack && (
              <Button type="button" variant="muted" size="lg" onClick={onBack}>
                بازگشت
              </Button>
            )}
          </div>
        </>
      ) : (
        <form
          onSubmit={codeForm.handleSubmit((v) => onVerify(v.code))}
          className="space-y-4"
        >
          <Field
            label={`کد برای ${phone}`}
            error={codeForm.formState.errors.code?.message}
          >
            <input
              {...codeForm.register("code")}
              inputMode="numeric"
              dir="ltr"
              maxLength={5}
              autoFocus
              className="h-12 w-full rounded-xl bg-input px-4 text-center text-lg tracking-[0.5em] outline-none focus:ring-2 focus:ring-ring/40 tnum"
              placeholder="—————"
            />
          </Field>
          {process.env.NEXT_PUBLIC_USE_MOCK === "true" && (
            <p className="text-xs text-muted-foreground">حالت ماک: کد تست در پاسخ API است.</p>
          )}
          {verifyError && <p className="text-sm text-destructive">کد وارد شده صحیح نیست.</p>}
          <Button type="submit" size="lg" className="w-full" disabled={verifyPending}>
            {verifyPending ? "در حال بررسی…" : "تأیید و ادامه"}
          </Button>
        </form>
      )}
    </div>
  );
}

function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-bold text-foreground">{label}</span>
      {children}
      {error && <span className="mt-1 block text-xs text-destructive">{error}</span>}
    </label>
  );
}
