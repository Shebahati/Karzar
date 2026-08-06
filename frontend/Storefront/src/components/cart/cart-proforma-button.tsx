"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Document } from "react-iconly";
import { Button } from "@/components/ui/button";
import { Field, fieldInputClass } from "@/components/ui/field";
import { useMe, useUpdateFullName } from "@/features/auth/queries";
import { isLoggedIn } from "@/lib/api-client";
import { downloadGuestCartProforma } from "@/services/proforma";
import { cn } from "@/lib/utils";
import type { CartLine } from "@/store/cart-store";

const LOGIN_GATE_MESSAGE = "برای دریافت پیش‌فاکتور وارد حساب شوید";
const NAME_GATE_TITLE = "نام شما برای پیش‌فاکتور لازم است";
const NAME_GATE_BODY =
  "پیش‌فاکتور باید به نام مشتری صادر شود. نام و نام خانوادگی‌تان را وارد کنید تا در حساب کاربری ذخیره شود و بالای پیش‌فاکتور به‌عنوان نام مشتری نمایش داده شود.";
const CART_RETURN = "/login?next=/cart";

type Gate = "login" | "name" | null;

/**
 * «دریافت پیش فاکتور» — cart sample HTML print.
 * Guests → login gate; logged-in without `full_name` → name gate; then print.
 */
export function CartProformaButton({
  lines,
  className,
  size = "lg",
  fullWidth = true,
  showHint = true,
}: {
  lines: CartLine[];
  className?: string;
  size?: "sm" | "md" | "lg";
  fullWidth?: boolean;
  showHint?: boolean;
}) {
  const router = useRouter();
  const { data: me, isLoading: meLoading } = useMe();
  const updateFullName = useUpdateFullName();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [gate, setGate] = useState<Gate>(null);
  const [nameDraft, setNameDraft] = useState("");
  const [nameError, setNameError] = useState<string | null>(null);
  const empty = lines.length === 0;

  const accountName = me?.full_name?.trim() ?? "";
  const waitingForProfile = isLoggedIn() && meLoading && !me;

  const openProforma = async (fullName: string, phone?: string | null) => {
    await downloadGuestCartProforma(lines, {
      fullName,
      phone: phone ?? me?.phone ?? null,
    });
  };

  const handleClick = async () => {
    if (empty || busy || waitingForProfile) return;
    setError(null);
    setNameError(null);

    if (!isLoggedIn()) {
      setGate("login");
      return;
    }

    if (!accountName) {
      setNameDraft("");
      setGate("name");
      return;
    }

    setGate(null);
    setBusy(true);
    try {
      await openProforma(accountName, me?.phone);
    } catch (err) {
      const code = err instanceof Error ? err.message : "";
      setError(
        code === "POPUP_BLOCKED"
          ? "پنجره پیش‌فاکتور مسدود شد. اجازه پاپ‌آپ را فعال کنید و دوباره بزنید."
          : "ساخت پیش‌فاکتور ناموفق بود. دوباره تلاش کنید.",
      );
    } finally {
      setBusy(false);
    }
  };

  const handleNameSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (busy) return;
    const trimmed = nameDraft.trim();
    if (trimmed.length < 2) {
      setNameError("نام و نام خانوادگی را کامل وارد کنید.");
      return;
    }

    setNameError(null);
    setError(null);
    setBusy(true);
    try {
      const updated = await updateFullName.mutateAsync(trimmed);
      const saved = updated.full_name?.trim() || trimmed;
      setGate(null);
      await openProforma(saved, updated.phone);
    } catch (err) {
      const code = err instanceof Error ? err.message : "";
      if (code === "FULL_NAME_TOO_SHORT") {
        setNameError("نام و نام خانوادگی را کامل وارد کنید.");
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
        onClick={() => void handleClick()}
      >
        <Document set="bold" size="small" />
        {busy ? "در حال ساخت…" : "دریافت پیش فاکتور"}
      </Button>
      {showHint && !gate && (
        <p className="mt-2 text-center text-[11px] leading-5 text-muted-foreground">
          پیش‌فاکتور سبد — چاپ یا ذخیره PDF · نیاز به ورود و نام مشتری
        </p>
      )}
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
      {gate === "name" && (
        <form
          role="dialog"
          aria-modal="false"
          aria-labelledby="proforma-name-gate-title"
          onSubmit={(e) => void handleNameSubmit(e)}
          className="mt-2 rounded-xl border border-border bg-card px-3 py-3 text-start shadow-soft"
        >
          <p
            id="proforma-name-gate-title"
            className="text-sm font-medium leading-6 text-foreground"
          >
            {NAME_GATE_TITLE}
          </p>
          <p className="mt-1.5 text-[12px] leading-5 text-muted-foreground">
            {NAME_GATE_BODY}
          </p>
          <Field
            label="نام و نام خانوادگی"
            error={nameError ?? undefined}
            className="mt-3"
          >
            <input
              value={nameDraft}
              onChange={(e) => {
                setNameDraft(e.target.value);
                if (nameError) setNameError(null);
              }}
              className={fieldInputClass}
              placeholder="مثال: رضا محمدی"
              autoComplete="name"
              disabled={busy}
            />
          </Field>
          <div className="mt-3 flex flex-wrap items-center justify-end gap-2">
            <Button
              type="button"
              size="sm"
              variant="ghost"
              disabled={busy}
              onClick={() => {
                setGate(null);
                setNameError(null);
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
