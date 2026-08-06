"use client";

import Link from "next/link";
import { useBrands } from "@/features/catalog/queries";
import { SafeImage } from "@/components/ui/safe-image";
import { AutoCarousel } from "@/components/ui/auto-carousel";
import { resolveBrandLogoUrl } from "@/config/brand-logos";
import { cn } from "@/lib/utils";
import type { Brand } from "@/types/category";

function BrandCard({
  name,
  logoUrl,
  id,
  slug,
}: {
  id: number;
  name: string;
  logoUrl?: string | null;
  slug?: string | null;
}) {
  const initial = (name || "B").slice(0, 1);
  const resolvedLogo = resolveBrandLogoUrl(name, logoUrl);
  const isSvg = Boolean(resolvedLogo?.toLowerCase().includes(".svg"));
  const href = slug?.trim() ? `/brands/${slug.trim()}` : `/catalog?brand=${id}`;

  return (
    <Link
      href={href}
      className={cn(
        "group relative flex h-[120px] w-[140px] flex-col overflow-hidden rounded-2xl sm:h-[132px] sm:w-[156px]",
        "bg-white",
        "ring-1 ring-inset ring-[#5E5F5E]/[0.08]",
        "shadow-[0_1px_0_rgba(94,95,94,0.04),0_8px_20px_-14px_rgba(94,95,94,0.22)]",
        "transition-[transform,box-shadow,ring-color] duration-300 ease-out",
        "md:hover:-translate-y-0.5 md:hover:ring-[#D02327]/15",
        "md:hover:shadow-[0_1px_0_rgba(94,95,94,0.05),0_14px_28px_-14px_rgba(208,35,39,0.12)]",
      )}
    >
      <span
        className={cn(
          "relative flex min-h-0 flex-1 items-center justify-center",
          "bg-[linear-gradient(165deg,#FBFBFB_0%,#F5F5F5_55%,#F0F0F0_100%)]",
          "px-3.5 py-3 sm:px-4 sm:py-3.5",
        )}
      >
        {resolvedLogo ? (
          <span className="relative h-full w-full">
            <SafeImage
              src={resolvedLogo}
              alt=""
              fill
              className="object-contain object-center transition-transform duration-500 md:group-hover:scale-[1.04]"
              sizes="156px"
              unoptimized={isSvg}
              fallback={
                <span className="grid h-full place-items-center text-3xl font-black text-[#5E5F5E]/25">
                  {initial}
                </span>
              }
            />
          </span>
        ) : (
          <span className="text-3xl font-black text-[#5E5F5E]/25">{initial}</span>
        )}
      </span>

      <span className="shrink-0 border-t border-[#5E5F5E]/[0.06] bg-white px-2.5 py-2">
        <span className="block truncate text-center text-[11px] font-bold tracking-tight text-[#5E5F5E] sm:text-xs">
          {name}
        </span>
      </span>
    </Link>
  );
}

/**
 * Brand strip for the home page.
 * Prefers RSC-passed brands so SSR HTML matches the hydrated client tree
 * (avoids shimmer ↔ BrandCard hydration mismatch).
 */
export function BrandStrip({ initialBrands = [] }: { initialBrands?: Brand[] }) {
  const { data } = useBrands();
  // Props from RSC prefetch win for first paint; query data takes over after hydrate/refetch.
  const brands = (data?.length ? data : initialBrands) ?? [];

  if (brands.length === 0) return null;

  // One pass is enough for manual scroll; avoid 2–3× DOM clones on mobile home.
  const loop = brands.length < 5 ? [...brands, ...brands] : brands;

  return (
    <div className="relative">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-y-2 -inset-x-1 rounded-3xl bg-[radial-gradient(120%_80%_at_50%_0%,rgba(208,35,39,0.035),transparent_55%)]"
      />
      <AutoCarousel
        itemClassName="w-auto"
        gapClass="gap-3 sm:gap-3.5"
        showControls
        trackClassName="px-0.5 pb-2"
      >
        {loop.map((brand, i) => (
          <BrandCard
            key={`${brand.id}-${i}`}
            id={brand.id}
            name={brand.name}
            logoUrl={brand.logo_url}
            slug={brand.slug}
          />
        ))}
      </AutoCarousel>
    </div>
  );
}
