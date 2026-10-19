import { readFileSync } from "node:fs";
import path from "node:path";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { Hero } from "@/components/home/hero";
import { parseDesignedHeroPack } from "@/features/home/hero-design";

const publishedPath = path.join(process.cwd(), "public", "hero-design.json");

function renderHeroWithPack() {
  const raw = JSON.parse(readFileSync(publishedPath, "utf8")) as unknown;
  const pack = parseDesignedHeroPack(raw);
  expect(pack).not.toBeNull();

  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return renderToStaticMarkup(
    <QueryClientProvider client={queryClient}>
      <Hero initialDesignedHeroPack={pack} />
    </QueryClientProvider>,
  );
}

describe("Hero SSR", () => {
  it("renders designed hero markup instead of loading skeleton when initial pack is provided", () => {
    const html = renderHeroWithPack();

    expect(html).toContain("تخفیف‌های ویژه‌ی کارزار");
    expect(html).toContain("/images/hero/reborn-5/calibrated-20261018/");
    expect(html).toContain("H01-special-offers-mobile-4x3.webp");
    expect(html).toContain("H01-special-offers-desktop-16x9.webp");
    expect(html).toContain("(max-width: 1023px)");
    expect(html).toContain("<picture");
    expect(html).not.toContain("animate-pulse");
  });
});
