import type { Metadata } from "next";
import { LoginView } from "@/components/auth/login-view";
import { NOINDEX_NOFOLLOW } from "@/lib/crawl-hygiene";

export const metadata: Metadata = {
  title: "ورود | ثبت‌نام",
  description: "ورود به حساب کاربری کارزار با شماره موبایل و کد یک‌بارمصرف.",
  robots: NOINDEX_NOFOLLOW,
};

export default function LoginPage() {
  return <LoginView />;
}
