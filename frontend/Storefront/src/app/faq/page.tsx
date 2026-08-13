import type { Metadata } from "next";
import { FaqPageShell } from "@/components/legal/faq-page-shell";
import { FAQ_INTRO, FAQ_CATEGORIES } from "@/components/legal/faq-content";
import { INDEXABLE_STATIC_CANONICALS, selfCanonicalAlternates } from "@/lib/crawl-hygiene";

export const metadata: Metadata = {
  title: "سوالات متداول",
  description:
    "پاسخ پرسش‌های پرتکرار فروشگاه کارزار درباره حساب کاربری، پیش‌فاکتور، فاکتور رسمی، سفارش، ارسال، مرجوعی و پشتیبانی.",
  alternates: selfCanonicalAlternates(INDEXABLE_STATIC_CANONICALS.faq),
};

export default function FaqPage() {
  return (
    <FaqPageShell
      eyebrow="راهنما"
      title="سوالات متداول"
      intro={FAQ_INTRO}
      categories={FAQ_CATEGORIES}
      sibling={{ label: "قوانین استفاده", href: "/terms" }}
    />
  );
}
