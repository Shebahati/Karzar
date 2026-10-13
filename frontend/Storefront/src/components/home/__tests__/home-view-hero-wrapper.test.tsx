import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

describe("HomeView hero wrapper", () => {
  it("does not impose fixed 62svh/100svh on the active hero outer wrapper", () => {
    const src = readFileSync(
      path.join(process.cwd(), "src/components/home/home-view.tsx"),
      "utf8",
    );
    const marker = "Hero owns its height";
    const idx = src.indexOf(marker);
    expect(idx).toBeGreaterThan(-1);
    const active = src.slice(idx);
    expect(active).not.toMatch(
      /<div className="relative h-\[62svh\][^"]*md:h-\[100svh\]">\s*\n\s*<Hero/,
    );
    expect(active).toMatch(
      /<div className="relative max-w-full overflow-x-clip \[overflow-anchor:none\]">\s*\n\s*<Hero/,
    );
  });
});
