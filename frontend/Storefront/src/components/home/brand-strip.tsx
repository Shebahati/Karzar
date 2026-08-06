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
  const displayName = name.split("|")[0]?.trim() || name;

  return (
    <Link
      href={href}
      title={displayName}
      aria-label={displayName}
      className={cn(
        // Slightly landscape “square-ish” tiles — Karzar logos are wide wordmarks;
        // this ratio + zero padding lets contain span left→right with no side gutters.
        "group relative block aspect-[5/4] w-[112px] overflow-hidden rounded-2xl sm:w-[128px] md:w-[140px]",
        "bg-white",
        "ring-1 ring-inset ring-[#5E5F5E]/[0.08]",
        "shadow-[0_1px_0_rgba(94,95,94,0.04),0_10px_22px_-14px_rgba(94,95,94,0.28)]",
        "transition-[transform,box-shadow,ring-color] duration-300 ease-out",
        "md:hover:-translate-y-0.5 md:hover:ring-[#D02327]/18",
        "md:hover:shadow-[0_1px_0_rgba(94,95,94,0.05),0_16px_30px_-14px_rgba(208,35,39,0.16)]",
      )}
    >
      {resolvedLogo ? (
        <SafeImage
          src={resolvedLogo}
          alt=""
          fill
          // Edge-to-edge: no px padding. Contain (not cover) — cover crops Mitutoyo/
          // Insize/Mighty Seven wordmarks. Scale nudges logos past the clip so the
          // card reads full-bleed without empty side gutters.
          className="object-contain object-center scale-[1.22] transition-transform duration-500 md:group-hover:scale-[1.28]"
          sizes="140px"
          unoptimized={isSvg}
          fallback={
            <span className="grid h-full place-items-center bg-white text-3xl font-black text-[#5E5F5E]/25">
              {initial}
            </span>
          }
        />
      ) : (
        <span className="grid h-full place-items-center bg-white text-3xl font-black text-[#5E5F5E]/25">
          {initial}
        </span>
      )}

      {/* Name only on hover — keeps logo full-bleed; still available via title/aria */}
      <span
        className={cn(
          "pointer-events-none absolute inset-x-0 bottom-0 z-[1]",
          "bg-gradient-to-t from-[#1a1a1a]/72 via-[#1a1a1a]/28 to-transparent",
          "px-2 pb-2 pt-8",
          "opacity-0 transition-opacity duration-300 md:group-hover:opacity-100",
        )}
      >
        <span className="block truncate text-center text-[10px] font-bold tracking-tight text-white sm:text-[11px]">
          {displayName}
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
    <div
      className={cn(
        "relative overflow-hidden rounded-[1.75rem] sm:rounded-[2rem]",
        "bg-[linear-gradient(165deg,#F4F4F4_0%,#EEEEEE_48%,#F6F6F6_100%)]",
        "p-3.5 sm:p-4 md:p-5",
        "ring-1 ring-inset ring-[#5E5F5E]/[0.07]",
        "shadow-[inset_0_1px_0_rgba(255,255,255,0.65)]",
      )}
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(90%_70%_at_70%_0%,rgba(208,35,39,0.06),transparent_52%)]"
      />
      <p
        aria-hidden
        className="pointer-events-none absolute -start-2 top-1/2 -translate-y-1/2 select-none text-[clamp(3.5rem,12vw,6.5rem)] font-black leading-none tracking-tight text-[#5E5F5E]/[0.045]"
      >
        Brands
      </p>

      <AutoCarousel
        itemClassName="w-auto"
        gapClass="gap-2.5 sm:gap-3"
        showControls
        // autoPlay defaults false — keep manual-only
        trackClassName="relative z-[1] px-0.5 pb-1"
        controlClassName="border-[#5E5F5E]/12 bg-white shadow-[0_6px_18px_-6px_rgba(94,95,94,0.4)]"
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
