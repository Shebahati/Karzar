import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = resolve(__dirname, "../../..");

describe("FE-001 design tokens", () => {
  it("defines shared section spacing and type CSS variables", () => {
    const css = readFileSync(resolve(ROOT, "src/app/globals.css"), "utf8");
    for (const token of [
      "--space-section-y",
      "--space-section-gap",
      "--type-section",
      "--type-section-lg",
      "--type-lede",
      "--type-lede-lg",
    ]) {
      expect(css).toContain(token);
    }
    expect(css).toContain(".home-stack");
    expect(css).toContain(".type-section");
    expect(css).toContain("no purple");
  });

  it("wires section spacing tokens into Tailwind theme", () => {
    const tw = readFileSync(resolve(ROOT, "tailwind.config.ts"), "utf8");
    expect(tw).toContain('"section-y"');
    expect(tw).toContain('"section-gap"');
    expect(tw).toContain("var(--space-section-y)");
    expect(tw).toContain("var(--type-section)");
  });

  it("home stack uses shared rhythm classes without double section padding", () => {
    const home = readFileSync(
      resolve(ROOT, "src/components/home/home-view.tsx"),
      "utf8",
    );
    expect(home).toContain("home-stack");
    // Page footer rhythm stays separate; section gap/padding come from .home-stack tokens.
    expect(home).not.toContain("pb-section-y");
    expect(home).toMatch(/pb-10/);
  });
});
