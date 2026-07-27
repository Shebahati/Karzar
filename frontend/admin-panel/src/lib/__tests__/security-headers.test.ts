import { describe, expect, it } from "vitest";
import { securityHeaders } from "@/lib/security-headers";

describe("admin security headers", () => {
  it("contains X-Robots-Tag noindex policy", () => {
    expect(securityHeaders).toEqual(
      expect.arrayContaining([
        { key: "X-Robots-Tag", value: "noindex, nofollow, noarchive" },
      ]),
    );
  });
});
