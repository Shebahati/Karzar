import type { Metadata } from "next";
import { LegalPageShell } from "@/components/legal/legal-page-shell";
import { PRIVACY_INTRO, PRIVACY_SECTIONS } from "@/components/legal/privacy-content";
import { LEGAL_POLICY_UPDATED_LABEL_FA } from "@/lib/legal-policy-meta";
import { INDEXABLE_STATIC_CANONICALS, selfCanonicalAlternates } from "@/lib/crawl-hygiene";

export const metadata: Metadata = {
  title: "حریم خصوصی",
  description:
    "سیاست حفظ حریم خصوصی فروشگاه اینترنتی کارزار؛ نحوهٔ جمع‌آوری، استفاده و نگهداری اطلاعات مشتریان.",
  alternates: selfCanonicalAlternates(INDEXABLE_STATIC_CANONICALS.privacy),
};

export default function PrivacyPage() {
  return (
    <LegalPageShell
      eyebrow="قوانین و مقررات"
      title="حریم خصوصی"
      intro={PRIVACY_INTRO}
      sections={PRIVACY_SECTIONS}
      updatedLabel={LEGAL_POLICY_UPDATED_LABEL_FA}
      sibling={{ label: "قوانین استفاده", href: "/terms" }}
    />
  );
}
