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
        "group relative block h-[150px] w-[180px] overflow-hidden rounded-[1.35rem] bg-[#F3F3F3] shadow-soft transition-all duration-400 sm:h-[170px] sm:w-[210px]",
        "hover:-translate-y-1 hover:shadow-elevated",
      )}
    >
      <span className="absolute inset-0 bottom-10 grid place-items-center bg-white sm:bottom-11">
        {resolvedLogo ? (
          <SafeImage
            src={resolvedLogo}
            alt=""
            fill
            className="object-contain p-5 pb-2 transition-transform duration-500 group-hover:scale-105 sm:p-6 sm:pb-3"
            sizes="210px"
            unoptimized={isSvg}
            fallback={<span className="text-4xl font-black text-steel/30">{initial}</span>}
          />
        ) : (
          <span className="text-4xl font-black text-steel/30">{initial}</span>
        )}
      </span>

      {/* Glass name strip */}
      <span className="absolute inset-x-0 bottom-0 border-t border-white/40 bg-white/55 px-3 py-2.5 backdrop-blur-xl supports-[backdrop-filter]:bg-white/40">
        <span className="block truncate text-center text-xs font-black tracking-tight text-foreground sm:text-sm">
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

  const loop = brands.length < 6 ? [...brands, ...brands, ...brands] : [...brands, ...brands];

  return (
    <AutoCarousel
      autoPlay
      intervalMs={2800}
      itemClassName="w-auto"
      gapClass="gap-3 sm:gap-4"
      showControls
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
  );
}
