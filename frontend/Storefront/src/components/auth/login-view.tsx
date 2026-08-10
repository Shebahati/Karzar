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

import { OTP_LENGTH, OTP_MOCK_CODE } from "@/lib/otp";
import { env } from "@/config/env";

type Step = "phone" | "otp";

/** Opacity-only — any x/y/scale transform on a focused ancestor triggers iOS Safari “zoom + side clip”. */
const stepMotion = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
  transition: { duration: 0.2 },
} as const;

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
  /** Guards auto-submit double-fire; cleared when the OTP value changes. */
  const autoSubmittedCodeRef = useRef<string | null>(null);
  const verifyInFlightRef = useRef(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    setExpiredBanner(params.get("expired") === "1");
  }, []);

  const requestOtp = useMutation({
    mutationFn: () => authService.requestOtp({ phone: toEnglishDigits(phone) }),
    onSuccess: (res) => {
      setCode(Array(OTP_LENGTH).fill(""));
      autoSubmittedCodeRef.current = null;
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
    onMutate: () => {
      verifyInFlightRef.current = true;
    },
    onSettled: () => {
      verifyInFlightRef.current = false;
    },
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

  // Focus first OTP cell after the opacity fade — never while a transform would be applied.
  useEffect(() => {
    if (step !== "otp") return;
    const t = window.setTimeout(() => {
      inputsRef.current[0]?.focus({ preventScroll: true });
    }, 220);
    return () => window.clearTimeout(t);
  }, [step]);

  const phoneValid = /^09\d{9}$/.test(toEnglishDigits(phone));
  const codeJoined = code.join("");
  const codeComplete = codeJoined.length === OTP_LENGTH && code.every((c) => c !== "");

  const submitOtp = (source: "auto" | "manual") => {
    if (!codeComplete || verifyInFlightRef.current || verifyOtp.isPending) return;
    if (source === "auto") {
      if (autoSubmittedCodeRef.current === codeJoined) return;
      autoSubmittedCodeRef.current = codeJoined;
    }
    verifyOtp.mutate();
  };

  // Auto-advance when all 6 digits are present (paste / typing). Button remains a fallback.
  useEffect(() => {
    if (step !== "otp" || !codeComplete) return;
    if (autoSubmittedCodeRef.current === codeJoined) return;
    if (verifyInFlightRef.current) return;
    const t = window.setTimeout(() => {
      if (verifyInFlightRef.current || autoSubmittedCodeRef.current === codeJoined) return;
      autoSubmittedCodeRef.current = codeJoined;
      verifyOtp.mutate();
    }, 180);
    return () => window.clearTimeout(t);
  }, [step, codeComplete, codeJoined, verifyOtp.mutate]);

  const handleCodeChange = (index: number, raw: string) => {
    const digits = toEnglishDigits(raw).replace(/\D/g, "");
    if (digits.length > 1) {
      // Paste / autofill into a single box — distribute across all inputs.
      const next = Array.from({ length: OTP_LENGTH }, (_, i) => digits[i] ?? "");
      autoSubmittedCodeRef.current = null;
      setCode(next);
      const focusIdx = Math.min(digits.length, OTP_LENGTH) - 1;
      inputsRef.current[Math.max(0, focusIdx)]?.focus({ preventScroll: true });
      return;
    }
    const value = digits.slice(-1);
    autoSubmittedCodeRef.current = null;
    setCode((prev) => {
      const next = [...prev];
      next[index] = value;
      return next;
    });
    if (value && index < OTP_LENGTH - 1) {
      inputsRef.current[index + 1]?.focus({ preventScroll: true });
    }
  };

  const handleCodePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pasted = toEnglishDigits(e.clipboardData.getData("text")).replace(/\D/g, "").slice(0, OTP_LENGTH);
    if (!pasted) return;
    autoSubmittedCodeRef.current = null;
    setCode(() => {
      const next = Array.from({ length: OTP_LENGTH }, (_, i) => pasted[i] ?? "");
      return next;
    });
    const focusIdx = Math.min(pasted.length, OTP_LENGTH) - 1;
    inputsRef.current[Math.max(0, focusIdx)]?.focus({ preventScroll: true });
  };

  const handleCodeKey = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace" && !code[index] && index > 0) {
      inputsRef.current[index - 1]?.focus({ preventScroll: true });
    }
  };

  return (
    /*
     * Mobile-safe shell:
     * - Full-viewport flex center (idle state must look centered, not top-stuck)
     * - svh (not vh) so URL-bar resize does not reflow as “zoom”
     * - overflow-x-clip on the shell only (not the shadowed card — that clips elevation)
     * - overflow-y-auto: when keyboard shrinks space, allow slight scroll without side clip
     * - no x/y/scale motion on step change (iOS focus + transform = side-clip zoom)
     */
    <div className="bg-hero-glow flex w-full max-w-full min-w-0 flex-col items-center justify-center overflow-x-clip overflow-y-auto px-4 py-10 sm:px-6 sm:py-14 min-h-[100svh] sm:min-h-[80svh]">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
        className="w-full min-w-0 max-w-md rounded-3xl border border-border/40 bg-card px-6 py-7 shadow-card sm:px-10 sm:py-11"
      >
        <div className="flex min-w-0 flex-col items-center text-center">
          <Logo variant="mark" height={36} />
          <h1 className="mt-5 text-xl font-bold tracking-arabic text-foreground sm:mt-6 sm:text-2xl">
            {step === "phone" ? "ورود | ثبت‌نام" : "تأیید شماره موبایل"}
          </h1>
          <p className="mt-2.5 max-w-[20.5rem] text-sm leading-6 text-muted-foreground sm:mt-3 sm:max-w-none">
            {step === "phone"
              ? "شماره موبایل خود را وارد کنید تا درخواست کد تأیید ثبت شود."
              : `اگر پیامک رسیده، کد ۶ رقمی ارسال‌شده به ${phone} را وارد کنید.`}
          </p>
        </div>

        <AnimatePresence mode="wait" initial={false}>
          {step === "phone" ? (
            <motion.form
              key="phone"
              {...stepMotion}
              onSubmit={(e) => {
                e.preventDefault();
                if (phoneValid) requestOtp.mutate();
              }}
              className="mt-7 flex flex-col gap-5 sm:mt-9 sm:gap-5"
            >
              <div className="relative min-w-0">
                <span className="pointer-events-none absolute start-4 top-1/2 -translate-y-1/2 text-muted-foreground">
                  <Call size="small" set="light" />
                </span>
                <input
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  inputMode="tel"
                  autoFocus
                  placeholder="۰۹XXXXXXXXX"
                  /* ≥16px — prevents iOS Safari focus auto-zoom */
                  className="h-12 w-full min-w-0 rounded-xl bg-input ps-11 pe-4 text-center text-base tracking-widest outline-none focus:ring-2 focus:ring-inset focus:ring-ring/40 tnum sm:h-13"
                />
              </div>

              {expiredBanner && (
                <p className="rounded-xl bg-warning/15 px-3.5 py-2.5 text-sm leading-6 text-foreground">
                  نشست شما منقضی شده؛ لطفاً دوباره وارد شوید.
                </p>
              )}

              {requestOtp.isError && (
                <p className="text-sm leading-6 text-destructive">ارسال کد ناموفق بود. دوباره تلاش کنید.</p>
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
                className="block text-center text-xs font-medium leading-5 text-muted-foreground transition-colors hover:text-primary"
              >
                رمز عبور دارید و آن را فراموش کرده‌اید؟ بازیابی دسترسی (رمز)
              </Link>
            </motion.form>
          ) : (
            <motion.form
              key="otp"
              {...stepMotion}
              onSubmit={(e) => {
                e.preventDefault();
                submitOtp("manual");
              }}
              className="mt-7 flex flex-col gap-5 sm:mt-9 sm:gap-6"
            >
              {/*
                flex-1 + basis-0 + gap-1.5 at narrow widths keeps 6 cells inside
                ~240–280px content at 320–360px. Inset ring avoids horizontal spill.
              */}
              <div dir="ltr" className="flex w-full min-w-0 max-w-full gap-1.5 sm:gap-2.5">
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
                    aria-label={`رقم ${i + 1} از ${OTP_LENGTH}`}
                    /* text-base = 16px — required to block iOS focus auto-zoom */
                    className="h-12 min-w-0 flex-1 basis-0 rounded-xl bg-input text-center text-base font-bold outline-none focus:ring-2 focus:ring-inset focus:ring-ring/40 tnum sm:h-14 sm:w-12 sm:flex-none sm:text-lg"
                  />
                ))}
              </div>

              {env.USE_MOCK && (
                <p className="text-center text-xs leading-5 text-muted-foreground">
                  حالت ماک محلی: کد تست{" "}
                  <span className="font-bold tnum" dir="ltr">
                    {OTP_MOCK_CODE}
                  </span>
                </p>
              )}

              {verifyOtp.isError && (
                <p className="text-center text-sm leading-6 text-destructive">
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

              <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2.5 text-sm">
                <button
                  type="button"
                  onClick={() => {
                    setStep("phone");
                    autoSubmittedCodeRef.current = null;
                  }}
                  className="flex items-center gap-1 font-bold text-muted-foreground transition-colors hover:text-foreground"
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

        <p className="mt-7 border-t border-border/40 pt-5 text-center text-xs leading-6 text-muted-foreground sm:mt-9 sm:pt-6">
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
