"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, Call, Lock } from "react-iconly";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/layout/logo";
import { authService } from "@/services/auth";
import { authKeys } from "@/features/auth/queries";
import { toEnglishDigits } from "@/lib/utils";

type Step = "phone" | "otp";
const OTP_LENGTH = 5;

function safeNextPath(raw: string | null): string {
  if (!raw) return "/";
  if (!raw.startsWith("/") || raw.startsWith("//") || raw.includes("://")) return "/";
  return raw;
}

export function LoginView() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [step, setStep] = useState<Step>("phone");
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState<string[]>(Array(OTP_LENGTH).fill(""));
  const [seconds, setSeconds] = useState(0);
  const [expiredBanner, setExpiredBanner] = useState(false);
  const inputsRef = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    setExpiredBanner(params.get("expired") === "1");
  }, []);

  const requestOtp = useMutation({
    mutationFn: () => authService.requestOtp({ phone: toEnglishDigits(phone) }),
    onSuccess: (res) => {
      setStep("otp");
      setSeconds(res.expires_in);
    },
  });

  const verifyOtp = useMutation({
    mutationFn: () =>
      authService.verifyOtp({
        phone: toEnglishDigits(phone),
        code: code.join(""),
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: authKeys.me });
      window.dispatchEvent(new Event("karzar-auth-change"));
      const params = new URLSearchParams(window.location.search);
      router.push(safeNextPath(params.get("next")));
    },
  });

  useEffect(() => {
    if (seconds <= 0) return;
    const t = setInterval(() => setSeconds((s) => s - 1), 1000);
    return () => clearInterval(t);
  }, [seconds]);

  const phoneValid = /^09\d{9}$/.test(toEnglishDigits(phone));
  const codeComplete = code.every((c) => c !== "");

  const handleCodeChange = (index: number, raw: string) => {
    const digits = toEnglishDigits(raw).replace(/\D/g, "");
    if (digits.length > 1) {
      // Paste / autofill into a single box — distribute across all inputs.
      setCode((prev) => {
        const next = [...prev];
        for (let i = 0; i < OTP_LENGTH; i++) {
          next[i] = digits[i] ?? "";
        }
        return next;
      });
      const focusIdx = Math.min(digits.length, OTP_LENGTH) - 1;
      inputsRef.current[Math.max(0, focusIdx)]?.focus();
      return;
    }
    const value = digits.slice(-1);
    setCode((prev) => {
      const next = [...prev];
      next[index] = value;
      return next;
    });
    if (value && index < OTP_LENGTH - 1) inputsRef.current[index + 1]?.focus();
  };

  const handleCodePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pasted = toEnglishDigits(e.clipboardData.getData("text")).replace(/\D/g, "").slice(0, OTP_LENGTH);
    if (!pasted) return;
    setCode((prev) => {
      const next = [...prev];
      for (let i = 0; i < OTP_LENGTH; i++) {
        next[i] = pasted[i] ?? "";
      }
      return next;
    });
    const focusIdx = Math.min(pasted.length, OTP_LENGTH) - 1;
    inputsRef.current[Math.max(0, focusIdx)]?.focus();
  };

  const handleCodeKey = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace" && !code[index] && index > 0) {
      inputsRef.current[index - 1]?.focus();
    }
  };

  return (
    <div className="bg-hero-glow grid min-h-[80vh] place-items-center px-5 py-12">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-md rounded-3xl bg-card p-8 shadow-elevated sm:p-10"
      >
        <div className="flex flex-col items-center text-center">
          <Logo />
          <h1 className="mt-6 text-xl font-bold text-foreground">
            {step === "phone" ? "ورود | ثبت‌نام" : "تأیید شماره موبایل"}
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {step === "phone"
              ? "شماره موبایل خود را وارد کنید تا درخواست کد تأیید ثبت شود."
              : `اگر پیامک رسیده، کد ۵ رقمی ارسال‌شده به ${phone} را وارد کنید.`}
          </p>
        </div>

        <AnimatePresence mode="wait">
          {step === "phone" ? (
            <motion.form
              key="phone"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              onSubmit={(e) => {
                e.preventDefault();
                if (phoneValid) requestOtp.mutate();
              }}
              className="mt-8 space-y-4"
            >
              <div className="relative">
                <span className="pointer-events-none absolute start-4 top-1/2 -translate-y-1/2 text-muted-foreground">
                  <Call size="small" set="light" />
                </span>
                <input
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  inputMode="tel"
                  autoFocus
                  placeholder="۰۹XXXXXXXXX"
                  className="h-13 w-full rounded-xl bg-input ps-11 pe-4 text-center text-base tracking-widest outline-none focus:ring-2 focus:ring-ring/40 tnum"
                />
              </div>

              {expiredBanner && (
                <p className="rounded-lg bg-warning/15 px-3 py-2 text-sm text-foreground">
                  نشست شما منقضی شده؛ لطفاً دوباره وارد شوید.
                </p>
              )}

              {requestOtp.isError && (
                <p className="text-sm text-destructive">ارسال کد ناموفق بود. دوباره تلاش کنید.</p>
              )}

              <Button
                type="submit"
                size="lg"
                className="w-full"
                disabled={!phoneValid || requestOtp.isPending}
              >
                {requestOtp.isPending ? "در حال ارسال…" : "دریافت کد تأیید"}
              </Button>

              <Link
                href="/account/security"
                className="block text-center text-xs font-medium text-muted-foreground hover:text-primary"
              >
                رمز عبور دارید و آن را فراموش کرده‌اید؟ بازیابی دسترسی (رمز)
              </Link>
            </motion.form>
          ) : (
            <motion.form
              key="otp"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              onSubmit={(e) => {
                e.preventDefault();
                if (codeComplete) verifyOtp.mutate();
              }}
              className="mt-8 space-y-5"
            >
                  <div dir="ltr" className="flex justify-center gap-2.5">
                {code.map((digit, i) => (
                  <input
                    key={i}
                    ref={(el) => {
                      inputsRef.current[i] = el;
                    }}
                    value={digit}
                    onChange={(e) => handleCodeChange(i, e.target.value)}
                    onKeyDown={(e) => handleCodeKey(i, e)}
                    onPaste={handleCodePaste}
                    inputMode="numeric"
                    autoComplete={i === 0 ? "one-time-code" : "off"}
                    maxLength={i === 0 ? OTP_LENGTH : 1}
                    autoFocus={i === 0}
                    aria-label={`رقم ${i + 1} از ${OTP_LENGTH}`}
                    className="h-14 w-12 rounded-xl bg-input text-center text-xl font-bold outline-none focus:ring-2 focus:ring-ring/40 tnum"
                  />
                ))}
              </div>

              {verifyOtp.isError && (
                <p className="text-center text-sm text-destructive">
                  کد وارد شده صحیح نیست.
                </p>
              )}

              <Button
                type="submit"
                size="lg"
                className="w-full gap-2"
                disabled={!codeComplete || verifyOtp.isPending}
              >
                <Lock size="small" set="bold" />
                {verifyOtp.isPending ? "در حال بررسی…" : "ورود به حساب"}
              </Button>

              <div className="flex items-center justify-between text-sm">
                <button
                  type="button"
                  onClick={() => setStep("phone")}
                  className="flex items-center gap-1 font-bold text-muted-foreground hover:text-foreground"
                >
                  <ArrowRight size="small" set="light" />
                  ویرایش شماره
                </button>
                {seconds > 0 ? (
                  <span className="text-muted-foreground tnum">
                    ارسال مجدد تا {seconds} ثانیه
                  </span>
                ) : (
                  <button
                    type="button"
                    onClick={() => requestOtp.mutate()}
                    className="font-bold text-primary"
                  >
                    ارسال مجدد کد
                  </button>
                )}
              </div>
            </motion.form>
          )}
        </AnimatePresence>

        <p className="mt-8 text-center text-xs leading-6 text-muted-foreground">
          ورود شما به منزله پذیرش{" "}
          <Link href="/terms" className="font-bold text-primary">
            قوانین و مقررات
          </Link>{" "}
          کارزار است.
        </p>
      </motion.div>
    </div>
  );
}
