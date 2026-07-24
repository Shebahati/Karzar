"use client";

import Link from "next/link";
import Image from "next/image";
import { useBrands } from "@/features/catalog/queries";
import { Skeleton } from "@/components/ui/skeleton";
import { AutoCarousel } from "@/components/ui/auto-carousel";
import { cn } from "@/lib/utils";

function BrandCard({
  name,
  country,
  logoUrl,
  id,
}: {
  id: number;
  name: string;
  country?: string | null;
  logoUrl?: string | null;
}) {
  const initial = (name || "B").slice(0, 1);

  return (
    <Link
      href={`/catalog?brand=${id}`}
      className={cn(
        "group relative flex h-[132px] w-[200px] flex-col justify-between overflow-hidden rounded-2xl border border-border/50 bg-card p-4 shadow-soft transition-all duration-300 sm:h-[148px] sm:w-[220px]",
        "hover:-translate-y-1 hover:border-steel/35 hover:shadow-glass",
      )}
    >
      <div className="pointer-events-none absolute -end-6 -top-6 h-24 w-24 rounded-full bg-steel/5 transition-transform duration-500 group-hover:scale-125" />
      <div className="relative flex items-center gap-3">
        <span className="grid h-12 w-12 shrink-0 place-items-center overflow-hidden rounded-xl bg-secondary text-base font-bold text-steel">
          {logoUrl ? (
            <Image src={logoUrl} alt="" width={48} height={48} className="object-contain p-1" />
          ) : (
            initial
          )}
        </span>
        <div className="min-w-0">
          <p className="truncate text-sm font-bold text-foreground">{name}</p>
          {country ? (
            <p className="mt-0.5 truncate text-xs text-steel">{country}</p>
          ) : (
            <p className="mt-0.5 text-xs text-muted-foreground">برند صنعتی</p>
          )}
        </div>
      </div>
      <div className="relative flex items-center justify-between">
        <span className="text-[10px] font-medium uppercase tracking-[0.14em] text-steel/70">
          Official
        </span>
        <span className="text-xs font-bold text-primary opacity-0 transition-opacity group-hover:opacity-100">
          مشاهده ←
        </span>
      </div>
    </Link>
  );
}

export function BrandStrip() {
  const { data, isLoading } = useBrands();

  if (isLoading) {
    return (
      <div className="flex gap-3 overflow-hidden">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-[132px] w-[200px] shrink-0 rounded-2xl" />
        ))}
      </div>
    );
  }

  const brands = data ?? [];
  if (!brands.length) return null;

  const loop = brands.length < 6 ? [...brands, ...brands, ...brands] : [...brands, ...brands];

  return (
    <AutoCarousel autoPlay intervalMs={3000} itemClassName="w-auto">
      {loop.map((brand, i) => (
        <BrandCard
          key={`${brand.id}-${i}`}
          id={brand.id}
          name={brand.name}
          country={brand.country}
          logoUrl={brand.logo_url}
        />
      ))}
    </AutoCarousel>
  );
}
