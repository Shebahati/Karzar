import { describe, expect, it } from "vitest";
import { FAQ_ITEMS } from "@/components/legal/faq-content";
import { PRIVACY_SECTIONS } from "@/components/legal/privacy-content";
import { TERMS_SECTIONS } from "@/components/legal/terms-content";
import { LEGAL_POLICY_UPDATED_LABEL_FA } from "@/lib/legal-policy-meta";

function sectionText(sections: { paragraphs: string[]; bullets?: string[] }[]): string {
  return sections
    .flatMap((s) => [...s.paragraphs, ...(s.bullets ?? [])])
    .join("\n");
}

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
  });

  it("FAQ aligns with Terms on returns, shipping, and authenticity", () => {
    const text = FAQ_ITEMS.map((i) => i.answer).join("\n");
    expect(text).toContain("۷ روز کاری");
    expect(text).not.toMatch(/تا ۷ روز(?!\s*کاری)/);
    expect(text).toContain("پس‌کرایه");
    expect(text).toContain("استرداد");
    expect(text).toContain("نمایندگی رسمی");
    expect(text).toContain("فقط وقتی مجاز است");
  });

  it("Privacy discloses GA4 and does not claim Clarity/Sentry are active", () => {
    const text = sectionText(PRIVACY_SECTIONS);
    expect(text).toMatch(/Google Analytics|GA4|gtag/i);
    expect(text).toContain("Clarity");
    expect(text).toContain("Sentry");
    expect(text).toMatch(/پیکربندی نشده|فعال در کد Storefront پیکربندی نشده/);
  });
});
