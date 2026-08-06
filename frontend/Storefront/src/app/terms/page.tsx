import type { Metadata } from "next";
import { LegalPageShell } from "@/components/legal/legal-page-shell";
import { TERMS_INTRO, TERMS_SECTIONS } from "@/components/legal/terms-content";

export const metadata: Metadata = {
  title: "قوانین استفاده",
  description:
    "شرایط و قوانین استفاده از فروشگاه اینترنتی کارزار؛ سفارش، پیش‌فاکتور، ارسال، مرجوعی و گارانتی.",
};

export default function TermsPage() {
  return (
    <LegalPageShell
      eyebrow="قوانین و مقررات"
      title="قوانین استفاده"
      intro={TERMS_INTRO}
      sections={TERMS_SECTIONS}
      sibling={{ label: "حریم خصوصی", href: "/privacy" }}
    />
  );
}
