import { describe, expect, it } from "vitest";
import { classifyVisit } from "../resolver";

describe("attribution resolver", () => {
  it("classifies torob utm", () => {
    const t = classifyVisit({
      landingPath: "/",
      referrer: null,
      utmSource: "torob",
      utmMedium: null,
      utmCampaign: null,
      capturedAt: new Date().toISOString(),
    });
    expect(t.source).toBe("torob");
  });
});
