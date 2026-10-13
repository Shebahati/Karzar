import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

describe("CheckoutPolicyNotice placement", () => {
  it("renders once per breakpoint (desktop body vs mobile dock)", () => {
    const src = readFileSync(
      path.resolve(__dirname, "../details-step.tsx"),
      "utf8",
    );
    expect(src).toMatch(
      /<CheckoutPolicyNotice[^>]*className="[^"]*hidden lg:block/,
    );
    expect(src).toMatch(
      /mobile-dock[\s\S]*<CheckoutPolicyNotice/,
    );
    const noticeCount = src.match(/<CheckoutPolicyNotice/g)?.length ?? 0;
    expect(noticeCount).toBe(2);
  });
});
