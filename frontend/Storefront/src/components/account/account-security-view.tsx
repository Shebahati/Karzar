"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Container } from "@/components/ui/container";
import { Button } from "@/components/ui/button";
import { authService } from "@/services/auth";
import { ApiError, isLoggedIn } from "@/lib/api-client";
import { toEnglishDigits } from "@/lib/utils";

function authErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    if (err.status === 429) {
      return err.retryAfterSeconds
        ? `تعداد درخواست‌ها زیاد است. حدود ${err.retryAfterSeconds} ثانیه صبر کنید.`
        : "تعداد درخواست‌ها زیاد است. کمی بعد دوباره تلاش کنید.";
    }
    if (err.status === 401 || err.status === 403) {
      return err.message || "احراز هویت ناموفق بود. دوباره وارد شوید.";
    }
    if (err.status === 400 || err.status === 422) {
      const detailMsg =
        Array.isArray(err.details) && err.details.length > 0
          ? String(
              (err.details[0] as { msg?: string; message?: string }).msg ??
                (err.details[0] as { message?: string }).message ??
                "",
            )
          : "";
      return detailMsg || err.message || fallback;
    }
    if (err.message) return err.message;
  }
  return fallback;
}

/**
 * Account security page. Reachable while logged OUT too (forgot-password OTP
 * flow), since that is precisely the case where a user has no session yet.
 * The "change password" form additionally requires an active session.
 */
export function AccountSecurityView() {
  const [authed, setAuthed] = useState(false);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    setAuthed(isLoggedIn());
  }, []);

  return (
    <Container className="max-w-lg py-8 lg:py-12">
      <Link href={authed ? "/account" : "/login"} className="text-sm text-primary">
        ← {authed ? "حساب کاربری" : "ورود"}
      </Link>
      <h1 className="mt-2 text-2xl font-bold text-foreground">امنیت حساب</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        ورود اصلی فروشگاه با پیامک (OTP) است. اگر برای حساب خود رمز عبور دارید، می‌توانید آن را عوض
        کنید یا در صورت فراموشی، با کد پیامکی بازیابی کنید.
      </p>

      {authed ? (
        <form
          className="mt-8 space-y-4 rounded-xl bg-card p-6 shadow-soft"
          onSubmit={(e) => {
            e.preventDefault();
            setErr(null);
            setMsg(null);
            setPending(true);
            void authService
              .changePassword({
                current_password: current,
                new_password: next,
              })
              .then(() => {
                setMsg("رمز عبور با موفقیت تغییر کرد.");
                setCurrent("");
                setNext("");
              })
              .catch((error) =>
                setErr(
                  authErrorMessage(
                    error,
                    "تغییر رمز ناموفق بود. رمز فعلی را بررسی کنید یا بعداً دوباره تلاش کنید.",
                  ),
                ),
              )
              .finally(() => setPending(false));
          }}
        >
          <h2 className="font-medium text-foreground">تغییر رمز عبور</h2>
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium">رمز فعلی</span>
            <input
              type="password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              className="h-11 w-full rounded-lg bg-input px-4 text-sm outline-none focus:ring-2 focus:ring-ring/40"
              dir="ltr"
            />
          </label>
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium">رمز جدید</span>
            <input
              type="password"
              value={next}
              onChange={(e) => setNext(e.target.value)}
              minLength={8}
              className="h-11 w-full rounded-lg bg-input px-4 text-sm outline-none focus:ring-2 focus:ring-ring/40"
              dir="ltr"
            />
          </label>
          {err && <p className="text-sm text-destructive">{err}</p>}
          {msg && <p className="text-sm text-success">{msg}</p>}
          <Button type="submit" disabled={pending || next.length < 8}>
            {pending ? "…" : "ذخیره رمز جدید"}
          </Button>
        </form>
      ) : (
        <div className="mt-8 rounded-xl bg-secondary px-4 py-3 text-sm text-foreground">
          برای تغییر رمز حساب فعلی، ابتدا{" "}
          <Link href="/login?next=/account/security" className="font-bold text-primary">
            وارد شوید
          </Link>
          . برای بازیابی رمز فراموش‌شده از فرم زیر استفاده کنید.
        </div>
      )}

      <PasswordResetBlock />
    </Container>
  );
}

function PasswordResetBlock() {
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [sent, setSent] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  return (
    <div className="mt-6 rounded-xl bg-card p-6 shadow-soft">
      <h2 className="font-medium text-foreground">بازیابی رمز (OTP)</h2>
      <p className="mt-1 text-xs text-muted-foreground">
        اگر رمز را فراموش کرده‌اید، با شماره موبایل کد تأیید بگیرید.
      </p>
      <div className="mt-4 space-y-3">
        <input
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          placeholder="۰۹XXXXXXXXX"
          className="h-11 w-full rounded-lg bg-input px-4 text-sm tnum outline-none focus:ring-2 focus:ring-ring/40"
          dir="ltr"
        />
        {!sent ? (
          <Button
            type="button"
            variant="outline"
            disabled={pending || !/^09\d{9}$/.test(toEnglishDigits(phone))}
            onClick={() => {
              setErr(null);
              setPending(true);
              void authService
                .requestPasswordReset(toEnglishDigits(phone))
                .then(() => {
                  setSent(true);
                  setMsg("اگر شماره معتبر باشد، کد ارسال می‌شود. صندوق پیامک را بررسی کنید.");
                })
                .catch((error) =>
                  setErr(
                    authErrorMessage(
                      error,
                      "درخواست بازیابی ناموفق بود. شماره را بررسی کنید یا کمی بعد دوباره تلاش کنید.",
                    ),
                  ),
                )
                .finally(() => setPending(false));
            }}
          >
            {pending ? "در حال ارسال…" : "دریافت کد"}
          </Button>
        ) : (
          <>
            <input
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="کد ۵ رقمی"
              className="h-11 w-full rounded-lg bg-input px-4 text-sm tnum outline-none focus:ring-2 focus:ring-ring/40"
              dir="ltr"
            />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="رمز جدید (حداقل ۸ کاراکتر)"
              className="h-11 w-full rounded-lg bg-input px-4 text-sm outline-none focus:ring-2 focus:ring-ring/40"
              dir="ltr"
            />
            <Button
              type="button"
              disabled={pending || password.length < 8 || toEnglishDigits(code).length < 4}
              onClick={() => {
                setErr(null);
                setPending(true);
                void authService
                  .confirmPasswordReset({
                    phone: toEnglishDigits(phone),
                    code: toEnglishDigits(code),
                    new_password: password,
                  })
                  .then(() => setMsg("رمز جدید ثبت شد. اکنون می‌توانید وارد شوید."))
                  .catch((error) =>
                    setErr(
                      authErrorMessage(
                        error,
                        "تأیید ناموفق بود. کد پیامک یا رمز جدید را بررسی کنید.",
                      ),
                    ),
                  )
                  .finally(() => setPending(false));
              }}
            >
              {pending ? "در حال ثبت…" : "ثبت رمز جدید"}
            </Button>
            <button
              type="button"
              className="text-xs font-medium text-muted-foreground hover:text-primary"
              onClick={() => {
                setSent(false);
                setCode("");
                setPassword("");
                setErr(null);
              }}
            >
              ارسال مجدد به شماره دیگر
            </button>
          </>
        )}
        {msg && (
          <p className="text-sm text-success">
            {msg}
            {msg.includes("وارد") && (
              <>
                {" "}
                <Link href="/login" className="font-bold underline-offset-2 hover:underline">
                  ورود به حساب
                </Link>
              </>
            )}
          </p>
        )}
        {err && <p className="text-sm text-destructive">{err}</p>}
      </div>
    </div>
  );
}
