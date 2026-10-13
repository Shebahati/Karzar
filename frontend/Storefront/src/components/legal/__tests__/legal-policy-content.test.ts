import { describe, expect, it } from "vitest";
import { FAQ_ITEMS } from "@/components/legal/faq-content";
import { PRIVACY_INTRO, PRIVACY_SECTIONS } from "@/components/legal/privacy-content";
import { TERMS_INTRO, TERMS_SECTIONS } from "@/components/legal/terms-content";
import { LEGAL_POLICY_UPDATED_LABEL_FA } from "@/lib/legal-policy-meta";

function sectionText(sections: { paragraphs: string[]; bullets?: string[] }[]): string {
  return sections
    .flatMap((s) => [...s.paragraphs, ...(s.bullets ?? [])])
    .join("\n");
}

const PUBLIC_LEGAL_TEXT = [
  TERMS_INTRO,
  sectionText(TERMS_SECTIONS),
  ...FAQ_ITEMS.map((i) => `${i.question}\n${i.answer}`),
  PRIVACY_INTRO,
  sectionText(PRIVACY_SECTIONS),
].join("\n");

describe("legal policy content (#251 / #262)", () => {
  it("uses current Persian policy revision label", () => {
    expect(LEGAL_POLICY_UPDATED_LABEL_FA).toContain("۲۱ مهر ۱۴۰۵");
    expect(LEGAL_POLICY_UPDATED_LABEL_FA).not.toContain("مرداد ۱۴۰۵");
  });

  it("Terms use ۷ روز کاری and qualified returns, not blanket calendar ۷ روز", () => {
    const text = sectionText(TERMS_SECTIONS);
    expect(text).toContain("۷ روز کاری");
    expect(text).not.toMatch(/تا ۷ روز(?!\s*کاری)/);
    expect(text).not.toContain("۷ روز بازگشت");
    expect(text).toContain("پس‌کرایه");
    expect(text).toMatch(/بازپرداخت|استرداد/);
    expect(text).not.toContain("warranty_text");
    expect(text).toMatch(/نمایندگی رسمی.*فقط در صورت|فقط وقتی مجاز است/);
    expect(text).not.toMatch(/\bSEP\b/);
    expect(text).not.toContain("checkout");
  });

  it("FAQ aligns with Terms on returns, shipping, and authenticity", () => {
    const text = FAQ_ITEMS.map((i) => i.answer).join("\n");
    expect(text).toContain("۷ روز کاری");
    expect(text).not.toMatch(/تا ۷ روز(?!\s*کاری)/);
    expect(text).toContain("پس‌کرایه");
    expect(text).toContain("استرداد");
    expect(text).toContain("نمایندگی رسمی");
    expect(text).toContain("فقط وقتی مجاز است");
    expect(text).not.toContain("base_price");
  });

  it("Privacy discloses GA4 without naming inactive analytics tools", () => {
    const text = sectionText(PRIVACY_SECTIONS);
    expect(text).toMatch(/Google Analytics|GA4|gtag/i);
    expect(text).not.toMatch(/Clarity|Sentry/i);
    expect(text).not.toContain("Storefront");
  });

  it("public legal surfaces omit internal schema identifiers", () => {
    expect(PUBLIC_LEGAL_TEXT).not.toContain("warranty_text");
    expect(PUBLIC_LEGAL_TEXT).not.toContain("base_price");
    expect(PUBLIC_LEGAL_TEXT).not.toMatch(/\bcheckout\b/i);
  });
});
