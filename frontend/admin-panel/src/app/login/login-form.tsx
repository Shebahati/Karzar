"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Lock, Login as LoginIcon, User } from "react-iconly";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { useLogin } from "@/features/auth/queries";
import { ApiError } from "@/lib/api-client";
import { isPasswordRequiredForLogin } from "@/lib/admin-settings";
import { env } from "@/config/env";
import { LogoMark } from "@/components/layout/logo";
import { authService } from "@/services/auth";
import { sanitizeNextPath } from "@/lib/sanitize-next-path";

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const login = useLogin();

  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [mockHint, setMockHint] = useState<{ phone: string; passwordHint: string } | null>(null);
  const [fieldErrors, setFieldErrors] = useState<{ phone?: string; password?: string }>({});
  const [restoring, setRestoring] = useState(true);

  const nextPath = sanitizeNextPath(searchParams.get("next"));
  const expired = searchParams.get("expired") === "1";
  const forbidden = searchParams.get("forbidden") === "1";
  const passwordRequired = isPasswordRequiredForLogin();

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      // Restore soft cookie + continue if an admin session already exists.
      if (authService.isAuthenticated()) {
        try {
          await authService.assertAdminSession();
          if (!cancelled) router.replace(nextPath);
          return;
        } catch {
          /* fall through to login form */
        }
      }

      if (env.USE_MOCK) {
        const { MOCK_ADMIN_CREDENTIALS } = await import("@/lib/mock-credentials");
        if (!cancelled) {
          setMockHint(MOCK_ADMIN_CREDENTIALS);
          setPhone(MOCK_ADMIN_CREDENTIALS.phone);
        }
      }

      if (!cancelled) setRestoring(false);
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, [nextPath, router]);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setFieldErrors({});

    if (!/^09\d{9}$/.test(phone.trim())) {
      setFieldErrors({ phone: "شماره موبایل معتبر وارد کنید (09XXXXXXXXX)" });
      return;
    }
    if (passwordRequired && password.length < 8) {
      setFieldErrors({ password: "رمز عبور باید حداقل ۸ کاراکتر باشد." });
      return;
    }

    try {
      await login.mutateAsync({
        phone_number: phone.trim(),
        password: passwordRequired ? password : "",
      });
      // Confirm role before entering the dashboard (live mode).
      await authService.assertAdminSession();
      toast.success("ورود موفق", { description: "به پنل مدیریت کارزار خوش آمدید." });
      router.replace(nextPath);
    } catch (err) {
      if (err instanceof Error && err.message === "FORBIDDEN") {
        toast.error("دسترسی مجاز نیست", {
          description: "این حساب مجوز ورود به پنل مدیریت را ندارد.",
        });
        return;
      }
      const message =
        err instanceof ApiError ? err.message : "ورود ناموفق بود. دوباره تلاش کنید.";
      toast.error("خطا در ورود", { description: message });
    }
  }

  if (restoring) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <p className="text-sm text-muted-foreground">در حال بررسی نشست…</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Card className="w-full max-w-md shadow-elevated">
        <CardHeader className="items-center text-center">
          <div className="mb-2 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-card">
            <LogoMark size={28} />
          </div>
          <CardTitle className="text-2xl">ورود به پنل کارزار</CardTitle>
          <p className="text-sm text-muted-foreground">
            {forbidden
              ? "حساب شما اجازهٔ دسترسی به پنل مدیریت را ندارد."
              : expired
                ? "نشست شما منقضی شده است. لطفاً دوباره وارد شوید."
                : mockHint
                  ? `با حساب سوپر ادمین وارد شوید (mock: ${mockHint.phone} / ${mockHint.passwordHint}).`
                  : "با حساب سوپر ادمین خود وارد شوید."}
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            <Field label="شماره موبایل" htmlFor="phone" required error={fieldErrors.phone}>
              <div className="relative">
                <span className="pointer-events-none absolute inset-y-0 start-3 flex items-center text-muted-foreground">
                  <User set="light" size={18} />
                </span>
                <Input
                  id="phone"
                  dir="ltr"
                  inputMode="tel"
                  autoComplete="username"
                  className="ps-10 text-start"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  disabled={login.isPending}
                />
              </div>
            </Field>

            <Field
              label="رمز عبور"
              htmlFor="password"
              required={passwordRequired}
              error={fieldErrors.password}
              hint={!passwordRequired ? "در حالت mock رمز اختیاری است" : undefined}
            >
              <div className="relative">
                <span className="pointer-events-none absolute inset-y-0 start-3 flex items-center text-muted-foreground">
                  <Lock set="light" size={18} />
                </span>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  className="ps-10"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={login.isPending}
                  placeholder={passwordRequired ? undefined : "اختیاری"}
                />
              </div>
            </Field>

            <Button type="submit" className="w-full" disabled={login.isPending}>
              <LoginIcon set="bold" size={20} primaryColor="#FFFFFF" />
              {login.isPending ? "در حال ورود..." : "ورود"}
            </Button>
          </form>

          {mockHint && (
            <p className="mt-6 text-center text-xs text-muted-foreground">
              محیط توسعه: {mockHint.phone} / {mockHint.passwordHint}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
