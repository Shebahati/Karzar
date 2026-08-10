"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Document } from "react-iconly";
import { Button } from "@/components/ui/button";
import { Field, fieldInputClass } from "@/components/ui/field";
import { useMe, useUpdateProfile } from "@/features/auth/queries";
import { isLoggedIn } from "@/lib/api-client";
import { joinFullName, splitFullName } from "@/lib/person-name";
import { formatBuyerAddressParts } from "@/lib/shipping";
import { downloadGuestCartProforma } from "@/services/proforma";
import { useAddressStore } from "@/store/address-store";
import { cn } from "@/lib/utils";
import type { CartLine } from "@/store/cart-store";

const LOGIN_GATE_MESSAGE = "برای دریافت پیش‌فاکتور وارد حساب شوید";
const BUYER_GATE_TITLE = "اطلاعات خریدار برای پیش‌فاکتور";
const BUYER_GATE_BODY =
  "پیش‌فاکتور به نام مشتری صادر می‌شود؛ نام و نام خانوادگی را وارد کنید.";
const CART_RETURN = "/login?next=/cart";
const ACCOUNT_ADDRESSES_HREF = "/account/addresses";
const CONTACT_HREF = "/contact";

type Gate = "login" | "buyer" | null;

/**
 * «دریافت پیش فاکتور» — cart sample HTML print.
 * Guests → login gate; logged-in with first+last → print;
 * missing name/family → buyer fields gate (company optional).
 */
export function CartProformaButton({
  lines,
  className,
  size = "lg",
  fullWidth = true,
}: {
  lines: CartLine[];
  className?: string;
  size?: "sm" | "md" | "lg";
  fullWidth?: boolean;
}) {
  const router = useRouter();
  const { data: me, isLoading: meLoading } = useMe();
  const updateProfile = useUpdateProfile();
  const getDefaultAddress = useAddressStore((s) => s.getDefault);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [gate, setGate] = useState<Gate>(null);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [firstError, setFirstError] = useState<string | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);
  const empty = lines.length === 0;

  const accountName = me?.full_name?.trim() ?? "";
  const waitingForProfile = isLoggedIn() && meLoading && !me;

  /** Same bar as buyer form: first + last each ≥ 2 chars. Company ignored. */
  const hasRegisteredBuyerName = (() => {
    const { first, last } = splitFullName(accountName);
    return first.length >= 2 && last.length >= 2;
  })();

  const openProforma = async (opts: {
    fullName: string;
    phone?: string | null;
    companyName?: string | null;
  }) => {
    const saved = getDefaultAddress();
    const parts = formatBuyerAddressParts(saved);
    await downloadGuestCartProforma(lines, {
      fullName: opts.fullName,
      phone: opts.phone ?? me?.phone ?? null,
      companyName: opts.companyName ?? null,
      address: parts.address || null,
      postalCode: parts.postalCode || null,
    });
  };

  const openBuyerGate = () => {
    const split = splitFullName(accountName);
    setFirstName(split.first);
    setLastName(split.last);
    setCompanyName(me?.company_name?.trim() ?? "");
    setFirstError(null);
    setLastError(null);
    setGate("buyer");
  };

  const handleClick = () => {
    if (empty || busy || waitingForProfile) return;
    setError(null);
    setFirstError(null);
    setLastError(null);

    if (!isLoggedIn()) {
      setGate("login");
      return;
    }

    if (hasRegisteredBuyerName) {
      setGate(null);
      setBusy(true);
      void (async () => {
        try {
          await openProforma({
            fullName: accountName,
            phone: me?.phone,
            companyName: me?.company_name?.trim() || null,
          });
        } catch (err) {
          const code = err instanceof Error ? err.message : "";
          if (code === "POPUP_BLOCKED") {
            setError(
              "پنجره پیش‌فاکتور مسدود شد. اجازه پاپ‌آپ را فعال کنید و دوباره بزنید.",
            );
          } else {
            setError("ساخت پیش‌فاکتور ناموفق بود. دوباره تلاش کنید.");
          }
        } finally {
          setBusy(false);
        }
      })();
      return;
    }

    openBuyerGate();
  };

  const handleBuyerSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (busy) return;

    const first = firstName.trim();
    const last = lastName.trim();
    const company = companyName.trim();
    let invalid = false;
    if (first.length < 2) {
      setFirstError("نام را کامل وارد کنید.");
      invalid = true;
    } else {
      setFirstError(null);
    }
    if (last.length < 2) {
      setLastError("نام خانوادگی را کامل وارد کنید.");
      invalid = true;
    } else {
      setLastError(null);
    }
    if (invalid) return;

    const fullName = joinFullName(first, last);
    setError(null);
    setBusy(true);
    try {
      const updated = await updateProfile.mutateAsync({
        full_name: fullName,
        company_name: company || null,
      });
      const saved = updated.full_name?.trim() || fullName;
      setGate(null);
      await openProforma({
        fullName: saved,
        phone: updated.phone,
        companyName: company || updated.company_name,
      });
    } catch (err) {
      const code = err instanceof Error ? err.message : "";
      if (code === "FULL_NAME_TOO_SHORT") {
        setFirstError("نام و نام خانوادگی را کامل وارد کنید.");
      } else if (code === "POPUP_BLOCKED") {
        setError(
          "پنجره پیش‌فاکتور مسدود شد. اجازه پاپ‌آپ را فعال کنید و دوباره بزنید.",
        );
      } else {
        setError("ذخیره نام یا ساخت پیش‌فاکتور ناموفق بود. دوباره تلاش کنید.");
      }
    } finally {
      setBusy(false);
    }
  };

  if (empty) return null;

  return (
    <div className={cn(fullWidth && "w-full", className)}>
      <Button
        type="button"
        variant="outline"
        size={size}
        className={cn(fullWidth && "w-full", "gap-2")}
        disabled={busy || waitingForProfile}
        aria-haspopup={gate ? "dialog" : undefined}
        onClick={handleClick}
      >
        <Document set="bold" size="small" />
        {busy ? "در حال ساخت…" : "دریافت پیش فاکتور"}
      </Button>
      <p className="mt-2 text-center text-[13px] leading-5 text-muted-foreground">
        برای پیش‌فاکتور رسمی{" "}
        <Link
          href={CONTACT_HREF}
          className="font-medium text-primary underline-offset-2 hover:underline"
        >
          با ما تماس بگیرید
        </Link>
      </p>
      {gate === "login" && (
        <div
          role="dialog"
          aria-modal="false"
          aria-labelledby="proforma-login-gate-title"
          className="mt-2 rounded-xl border border-border bg-card px-3 py-3 text-center shadow-soft"
        >
          <p
            id="proforma-login-gate-title"
            className="text-sm font-medium leading-6 text-foreground"
          >
            {LOGIN_GATE_MESSAGE}
          </p>
          <div className="mt-3 flex flex-wrap items-center justify-center gap-2">
            <Button
              type="button"
              size="sm"
              className="min-w-[7.5rem]"
              onClick={() => router.push(CART_RETURN)}
            >
              ورود به حساب
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => setGate(null)}
            >
              انصراف
            </Button>
          </div>
        </div>
      )}
      {gate === "buyer" && (
        <form
          role="dialog"
          aria-modal="false"
          aria-labelledby="proforma-buyer-gate-title"
          onSubmit={(e) => void handleBuyerSubmit(e)}
          className="mt-2 rounded-xl border border-border bg-card px-3 py-3 text-start shadow-soft"
        >
          <p
            id="proforma-buyer-gate-title"
            className="text-sm font-medium leading-6 text-foreground"
          >
            {BUYER_GATE_TITLE}
          </p>
          <p className="mt-1.5 text-[12px] leading-5 text-muted-foreground">
            {BUYER_GATE_BODY}
          </p>
          <Field label="نام" error={firstError ?? undefined} className="mt-3">
            <input
              value={firstName}
              onChange={(e) => {
                setFirstName(e.target.value);
                if (firstError) setFirstError(null);
              }}
              className={fieldInputClass}
              placeholder="مثال: رضا"
              autoComplete="given-name"
              disabled={busy}
            />
          </Field>
          <Field
            label="نام خانوادگی"
            error={lastError ?? undefined}
            className="mt-2"
          >
            <input
              value={lastName}
              onChange={(e) => {
                setLastName(e.target.value);
                if (lastError) setLastError(null);
              }}
              className={fieldInputClass}
              placeholder="مثال: محمدی"
              autoComplete="family-name"
              disabled={busy}
            />
          </Field>
          <Field label="اسم شرکت (اختیاری)" className="mt-2">
            <input
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              className={fieldInputClass}
              placeholder="در صورت خرید سازمانی"
              autoComplete="organization"
              disabled={busy}
            />
          </Field>
          <p className="mt-2 text-[12px] leading-5 text-muted-foreground">
            برای تکمیل اطلاعات پیش‌فاکتور، می‌توانید نشانی خود را در{" "}
            <Link
              href={ACCOUNT_ADDRESSES_HREF}
              className="font-medium text-primary underline-offset-2 hover:underline"
            >
              حساب کاربری
            </Link>{" "}
            ثبت کنید تا در پیش‌فاکتور درج شود.
          </p>
          <div className="mt-3 flex flex-wrap items-center justify-end gap-2">
            <Button
              type="button"
              size="sm"
              variant="ghost"
              disabled={busy}
              onClick={() => {
                setGate(null);
                setFirstError(null);
                setLastError(null);
              }}
            >
              انصراف
            </Button>
            <Button type="submit" size="sm" className="min-w-[9rem]" disabled={busy}>
              {busy ? "در حال ذخیره…" : "ذخیره و دریافت"}
            </Button>
          </div>
        </form>
      )}
      {error && (
        <p className="mt-1 text-center text-xs text-destructive" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
