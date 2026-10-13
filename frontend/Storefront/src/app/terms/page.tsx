import type { Metadata } from "next";
import { LegalPageShell } from "@/components/legal/legal-page-shell";
import { TERMS_INTRO, TERMS_SECTIONS } from "@/components/legal/terms-content";
import { LEGAL_POLICY_UPDATED_LABEL_FA } from "@/lib/legal-policy-meta";
import { INDEXABLE_STATIC_CANONICALS, selfCanonicalAlternates } from "@/lib/crawl-hygiene";

export const metadata: Metadata = {
  title: "قوانین استفاده",
  description:
    "شرایط و قوانین استفاده از فروشگاه اینترنتی کارزار؛ سفارش، پیش‌فاکتور، ارسال، مرجوعی و گارانتی.",
  alternates: selfCanonicalAlternates(INDEXABLE_STATIC_CANONICALS.terms),
};

export default function TermsPage() {
  return (
    <LegalPageShell
      eyebrow="قوانین و مقررات"
      title="قوانین استفاده"
      intro={TERMS_INTRO}
      sections={TERMS_SECTIONS}
      updatedLabel={LEGAL_POLICY_UPDATED_LABEL_FA}
      sibling={{ label: "حریم خصوصی", href: "/privacy" }}
    />
  );
}
