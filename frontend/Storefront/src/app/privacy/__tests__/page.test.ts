import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import PrivacyPage, { metadata } from "@/app/privacy/page";
import { INDEXABLE_STATIC_CANONICALS } from "@/lib/crawl-hygiene";

describe("/privacy page", () => {
  it("does not redirect to FAQ", () => {
    const src = readFileSync(
      path.resolve(__dirname, "../page.tsx"),
      "utf8",
    );
    expect(src).not.toContain('redirect("/faq")');
    expect(src).not.toContain("redirect('/faq')");
    expect(typeof PrivacyPage).toBe("function");
  });

  it("declares self-canonical metadata", () => {
    expect(metadata.alternates?.canonical).toBe(
      INDEXABLE_STATIC_CANONICALS.privacy,
    );
  });
});
