import { describe, expect, it } from "vitest";

import { resolveTheme } from "@/lib/theme";

describe("theme", () => {
  it("resolves explicit modes", () => {
    expect(resolveTheme("light")).toBe("light");
    expect(resolveTheme("dark")).toBe("dark");
  });
});
