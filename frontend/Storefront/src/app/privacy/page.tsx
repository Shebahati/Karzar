import type { Metadata } from "next";
import { LegalPageShell } from "@/components/legal/legal-page-shell";
import {
  PRIVACY_INTRO,
  PRIVACY_SECTIONS,
} from "@/components/legal/privacy-content";

export const metadata: Metadata = {
  title: "حریم خصوصی",
  description:
    "سیاست حفظ حریم خصوصی کاربران فروشگاه کارزار؛ جمع‌آوری، استفاده و امنیت داده‌ها.",
};

export default function PrivacyPage() {
  return (
    <LegalPageShell
      eyebrow="حریم خصوصی"
      title="حریم خصوصی"
      intro={PRIVACY_INTRO}
      sections={PRIVACY_SECTIONS}
      sibling={{ label: "قوانین استفاده", href: "/terms" }}
    />
  );
}
