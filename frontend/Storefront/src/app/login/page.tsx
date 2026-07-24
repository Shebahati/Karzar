import type { Metadata } from "next";
import { LoginView } from "@/components/auth/login-view";

export const metadata: Metadata = {
  title: "ورود | ثبت‌نام",
  description: "ورود به حساب کاربری کارزار با شماره موبایل و کد یک‌بارمصرف.",
};

export default function LoginPage() {
  return <LoginView />;
}
