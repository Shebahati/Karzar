"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, Work } from "react-iconly";
import { Container } from "@/components/ui/container";
import { Button } from "@/components/ui/button";
import { Field, fieldInputClass } from "@/components/ui/field";
import { Skeleton } from "@/components/ui/skeleton";
import { useMe, useUpdateProfile } from "@/features/auth/queries";
import { isLoggedIn } from "@/lib/api-client";
import { joinFullName, splitFullName } from "@/lib/person-name";
import { cn, toPersianDigits } from "@/lib/utils";

type Panel = "personal" | "company";

export function AccountProfileView() {
  const router = useRouter();
  const [authReady, setAuthReady] = useState(false);
  const [hasToken, setHasToken] = useState(false);
  const { data: me, isLoading } = useMe(authReady && hasToken);
  const updateProfile = useUpdateProfile();

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [panel, setPanel] = useState<Panel>("personal");
  const [firstError, setFirstError] = useState<string | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);
  const [companyError, setCompanyError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const ok = isLoggedIn();
    setHasToken(ok);
    setAuthReady(true);
    if (!ok) router.replace("/login?next=/account/profile");
  }, [router]);

  useEffect(() => {
    if (!me || hydrated) return;
    const split = splitFullName(me.full_name ?? "");
    setFirstName(split.first);
    setLastName(split.last);
    setCompanyName(me.company_name?.trim() ?? "");
    setHydrated(true);
  }, [me, hydrated]);

  const isCorporate = Boolean(me?.is_b2b);
  const incomplete = !me?.full_name?.trim();

  if (!authReady || !hasToken) {
    return (
      <Container className="py-16">
        <p className="text-center text-sm text-steel">در حال هدایت به ورود…</p>
      </Container>
    );
  }

  const validate = (): boolean => {
    let invalid = false;
    const first = firstName.trim();
    const last = lastName.trim();
    const company = companyName.trim();

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
    if (isCorporate && company.length < 2) {
      setCompanyError("نام شرکت را وارد کنید.");
      invalid = true;
      if (panel !== "company") setPanel("company");
    } else if (company.length > 120) {
      setCompanyError("نام شرکت نباید بیش از ۱۲۰ کاراکتر باشد.");
      invalid = true;
    } else {
      setCompanyError(null);
    }
    return !invalid;
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    setSuccess(null);
    setFormError(null);
    if (!validate()) return;

    const full_name = joinFullName(firstName, lastName);
    const company_name = companyName.trim() || null;

    updateProfile.mutate(
      { full_name, company_name },
      {
        onSuccess: () => {
          setSuccess(
            incomplete
              ? "اطلاعات کاربری شما تکمیل و ذخیره شد."
              : "تغییرات با موفقیت ذخیره شد.",
          );
        },
        onError: (err) => {
          const code = err.message;
          if (code === "FULL_NAME_TOO_SHORT") {
            setFirstError("نام و نام خانوادگی را کامل وارد کنید.");
            setPanel("personal");
          } else if (code === "COMPANY_NAME_TOO_LONG") {
            setCompanyError("نام شرکت نباید بیش از ۱۲۰ کاراکتر باشد.");
            if (isCorporate) setPanel("company");
          } else {
            setFormError("ذخیره اطلاعات ناموفق بود. کمی بعد دوباره تلاش کنید.");
          }
        },
      },
    );
  };

  return (
    <Container className="max-w-xl py-8 lg:py-12">
      <Link
        href="/account"
        className="inline-flex items-center gap-1 text-sm text-primary"
      >
        <ArrowRight size="small" set="light" primaryColor="#D02327" />
        حساب کاربری
      </Link>
      <h1 className="mt-2 text-2xl font-bold text-foreground">
        {incomplete ? "تکمیل اطلاعات کاربری" : "ویرایش اطلاعات کاربری"}
      </h1>
      <p className="mt-1 text-sm leading-6 text-steel">
        {isCorporate
          ? "اطلاعات شخصی و شرکتی حساب خود را بررسی و به‌روز کنید."
          : "نام و مشخصات نمایشی حساب را تکمیل کنید؛ در صورت نیاز نام شرکت را هم می‌توانید اضافه کنید."}
      </p>

      {isLoading && !hydrated ? (
        <div className="mt-8 space-y-3">
          <Skeleton className="h-12 w-full rounded-xl" />
          <Skeleton className="h-12 w-full rounded-xl" />
          <Skeleton className="h-12 w-full rounded-xl" />
        </div>
      ) : (
        <form
          onSubmit={onSubmit}
          className="relative mt-8 overflow-hidden rounded-3xl border border-border/40 bg-card p-5 shadow-soft sm:p-7"
        >
          <div
            className="pointer-events-none absolute inset-0 opacity-[0.06]"
            style={{
              background:
                "radial-gradient(ellipse at 100% 0%, #D02327 0%, transparent 55%), radial-gradient(ellipse at 0% 100%, #5E5F5E 0%, transparent 50%)",
            }}
          />

          <div className="relative">
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[11px] font-bold",
                  isCorporate
                    ? "bg-primary/10 text-primary"
                    : "bg-secondary text-steel",
                )}
              >
                {isCorporate ? (
                  <>
                    <Work set="bold" size="small" />
                    حساب شرکتی
                  </>
                ) : (
                  "حساب شخصی"
                )}
              </span>
              {me?.phone ? (
                <span className="text-xs text-steel tnum">
                  {toPersianDigits(me.phone)}
                </span>
              ) : null}
            </div>

            {isCorporate ? (
              <div
                role="tablist"
                aria-label="بخش اطلاعات"
                className="mt-5 grid grid-cols-2 gap-1 rounded-2xl bg-secondary/80 p-1"
              >
                <button
                  type="button"
                  role="tab"
                  aria-selected={panel === "personal"}
                  className={cn(
                    "rounded-xl px-3 py-2.5 text-sm font-bold transition-colors",
                    panel === "personal"
                      ? "bg-card text-foreground shadow-soft"
                      : "text-steel hover:text-foreground",
                  )}
                  onClick={() => setPanel("personal")}
                >
                  اطلاعات شخصی
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={panel === "company"}
                  className={cn(
                    "rounded-xl px-3 py-2.5 text-sm font-bold transition-colors",
                    panel === "company"
                      ? "bg-card text-foreground shadow-soft"
                      : "text-steel hover:text-foreground",
                  )}
                  onClick={() => setPanel("company")}
                >
                  اطلاعات شرکت
                </button>
              </div>
            ) : null}

            <div
              className={cn(
                "mt-5 space-y-4",
                isCorporate && panel !== "personal" && "hidden",
              )}
              role={isCorporate ? "tabpanel" : undefined}
            >
              {!isCorporate ? (
                <p className="text-xs leading-5 text-muted-foreground">
                  شماره موبایل از طریق ورود پیامکی ثابت است و از اینجا تغییر
                  نمی‌کند.
                </p>
              ) : null}
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="نام" error={firstError ?? undefined}>
                  <input
                    value={firstName}
                    onChange={(e) => {
                      setFirstName(e.target.value);
                      if (firstError) setFirstError(null);
                      if (success) setSuccess(null);
                    }}
                    className={fieldInputClass}
                    placeholder="مثال: رضا"
                    autoComplete="given-name"
                    disabled={updateProfile.isPending}
                  />
                </Field>
                <Field label="نام خانوادگی" error={lastError ?? undefined}>
                  <input
                    value={lastName}
                    onChange={(e) => {
                      setLastName(e.target.value);
                      if (lastError) setLastError(null);
                      if (success) setSuccess(null);
                    }}
                    className={fieldInputClass}
                    placeholder="مثال: محمدی"
                    autoComplete="family-name"
                    disabled={updateProfile.isPending}
                  />
                </Field>
              </div>
              <Field
                label="موبایل"
                hint="از طریق ورود پیامکی ثبت شده و قابل ویرایش نیست."
              >
                <input
                  value={me?.phone ? toPersianDigits(me.phone) : "—"}
                  readOnly
                  className={cn(fieldInputClass, "tnum text-steel opacity-80")}
                  dir="ltr"
                />
              </Field>
              {!isCorporate ? (
                <Field
                  label="نام شرکت (اختیاری)"
                  hint="اگر خرید سازمانی دارید، نام شرکت را وارد کنید."
                  error={companyError ?? undefined}
                >
                  <input
                    value={companyName}
                    onChange={(e) => {
                      setCompanyName(e.target.value);
                      if (companyError) setCompanyError(null);
                      if (success) setSuccess(null);
                    }}
                    className={fieldInputClass}
                    placeholder="در صورت نیاز"
                    autoComplete="organization"
                    disabled={updateProfile.isPending}
                  />
                </Field>
              ) : null}
            </div>

            {isCorporate ? (
              <div
                className={cn("mt-5 space-y-4", panel !== "company" && "hidden")}
                role="tabpanel"
              >
                <p className="text-xs leading-5 text-muted-foreground">
                  جزئیات شرکت روی فاکتور و پیش‌فاکتور سازمانی نمایش داده می‌شود.
                </p>
                <Field
                  label="نام شرکت"
                  error={companyError ?? undefined}
                  hint="برای حساب شرکتی، نام شرکت الزامی است."
                >
                  <input
                    value={companyName}
                    onChange={(e) => {
                      setCompanyName(e.target.value);
                      if (companyError) setCompanyError(null);
                      if (success) setSuccess(null);
                    }}
                    className={fieldInputClass}
                    placeholder="مثال: شرکت صنایع نمونه"
                    autoComplete="organization"
                    disabled={updateProfile.isPending}
                  />
                </Field>
              </div>
            ) : null}

            {formError ? (
              <p className="mt-4 text-sm text-destructive" role="alert">
                {formError}
              </p>
            ) : null}
            {success ? (
              <p
                className="mt-4 rounded-xl bg-success/10 px-3 py-2.5 text-sm leading-6 text-success"
                role="status"
              >
                {success}
              </p>
            ) : null}

            <div className="mt-6 flex flex-wrap items-center gap-2">
              <Button
                type="submit"
                className="min-w-[9.5rem]"
                disabled={updateProfile.isPending}
              >
                {updateProfile.isPending
                  ? "در حال ذخیره…"
                  : incomplete
                    ? "تکمیل و ذخیره"
                    : "ذخیره تغییرات"}
              </Button>
              <Button
                type="button"
                variant="ghost"
                disabled={updateProfile.isPending}
                onClick={() => router.push("/account")}
              >
                بازگشت
              </Button>
            </div>
          </div>
        </form>
      )}
    </Container>
  );
}
