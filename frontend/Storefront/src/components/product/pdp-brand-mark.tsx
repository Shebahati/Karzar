"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { CategoryVisualIcon } from "@/components/ui/category-visual-icon";
import { SafeImage } from "@/components/ui/safe-image";
import { resolveBrandLogoUrl } from "@/config/brand-logos";
import {
  isCategoryIconUrl,
  resolveCategoryIconUrl,
} from "@/config/category-icons";
import { categoryHref } from "@/config/nav-groups";
import { cn } from "@/lib/utils";
import type { Brand, CategoryFlat } from "@/types/category";
import type { BrandBrief } from "@/types/product";

type IdentityCategory = Pick<
  CategoryFlat,
  "id" | "name" | "slug" | "icon" | "image_url"
>;

const plate =
  "bg-[linear-gradient(160deg,#FFFFFF_0%,#F6F5F3_100%)] ring-1 ring-steel/[0.08] shadow-[0_6px_18px_-8px_rgba(94,95,94,0.3)] transition-[transform,box-shadow] duration-300 group-hover:scale-[1.01] group-hover:ring-steel/[0.14]";

/** Mark tile height — brand plate + category square share this. */
const MARK_H = "h-16 sm:h-[4.5rem]";
const CAT_W = "w-16 sm:w-[4.5rem]";

/**
 * Brand (+ optional category) identity for PDP buy column.
 * `quiet`: sits directly above the sticky buy card; row stretches to 100% of
 * that column (brand flex-1 + category square). Names under marks only —
 * no «برند»/«دسته» captions. Category mark has no plate/bg/ring.
 * Renders only when `brand` is present — category alone is never shown.
 */
export function PdpBrandMark({
  brand,
  logoUrl,
  category,
  className,
  animate = true,
  density = "default",
}: {
  brand?: BrandBrief | null;
  /** Full brand row logo when available from brands list. */
  logoUrl?: string | null;
  /** L1 / resolved category for square icon + label. */
  category?: IdentityCategory | null;
  className?: string;
  animate?: boolean;
  density?: "default" | "quiet";
}) {
  const reduced = useReducedMotion();
  const quiet = density === "quiet";

  /* Brand required — never show category-alone row (looks sparse). */
  if (!brand) return null;

  if (quiet) {
    const paired = Boolean(category);
    const row = (
      <div
        className={cn(
          /* Exact buy-column width: brand grows, category fixed square */
          paired
            ? "grid w-full min-w-0 max-w-full grid-cols-[minmax(0,1fr)_auto] items-start gap-2.5 sm:gap-3"
            : "flex w-full min-w-0 max-w-full flex-row items-start",
          className,
        )}
      >
        <QuietBrandColumn brand={brand} logoUrl={logoUrl} paired={paired} />
        {category ? <QuietCategoryColumn category={category} /> : null}
      </div>
    );

    if (!animate || reduced) return row;

    return (
      <motion.div
        className="w-full min-w-0 max-w-full"
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
      >
        {row}
      </motion.div>
    );
  }

  return (
    <DefaultBrandRow
      brand={brand}
      logoUrl={logoUrl}
      className={className}
      animate={animate}
      reduced={Boolean(reduced)}
    />
  );
}

function QuietBrandColumn({
  brand,
  logoUrl,
  paired,
}: {
  brand: BrandBrief;
  logoUrl?: string | null;
  paired: boolean;
}) {
  const href = brand.slug?.trim()
    ? `/brands/${brand.slug.trim()}`
    : `/catalog?brand=${brand.id}`;
  const resolved = resolveBrandLogoUrl(brand.name, logoUrl);
  const isSvg = Boolean(resolved?.toLowerCase().includes(".svg"));
  const initial = (brand.name || "B").trim().slice(0, 1);

  return (
    <Link
      href={href}
      className={cn(
        "group flex min-w-0 flex-col items-stretch gap-2.5 sm:gap-3 outline-none",
        paired ? "w-full" : "w-full",
        "focus-visible:rounded-xl focus-visible:ring-2 focus-visible:ring-primary/35 focus-visible:ring-offset-2",
      )}
      aria-label={`برند ${brand.name}`}
    >
      <span
        className={cn(
          "relative grid w-full place-items-center overflow-hidden rounded-xl sm:rounded-[0.9rem]",
          plate,
          MARK_H,
        )}
      >
        {resolved ? (
          <SafeImage
            src={resolved}
            alt=""
            fill
            sizes={
              paired
                ? "(min-width: 1024px) 180px, 50vw"
                : "(min-width: 1024px) 240px, 70vw"
            }
            className="object-contain object-center p-2.5 lg:object-cover lg:p-0"
            unoptimized={isSvg}
            fallback={
              <span className="text-base font-bold text-steel/35">{initial}</span>
            }
          />
        ) : (
          <span className="text-base font-bold text-steel/35">{initial}</span>
        )}
      </span>
      <span className="min-w-0 text-center">
        <span className="block text-[11px] font-semibold leading-snug tracking-tight text-foreground transition-colors group-hover:text-primary">
          {brand.name}
          {brand.country ? (
            <span className="font-medium text-steel/80"> · {brand.country}</span>
          ) : null}
        </span>
      </span>
    </Link>
  );
}

function QuietCategoryColumn({ category }: { category: IdentityCategory }) {
  const icon =
    resolveCategoryIconUrl({
      name: category.name,
      slug: category.slug,
      icon: category.icon,
      image_url: category.image_url,
    }) ?? category.icon;
  const fillUrl = isCategoryIconUrl(icon) ? icon : null;
  const longName = category.name.trim().length > 14;

  return (
    <Link
      href={categoryHref(category)}
      className={cn(
        "group flex shrink-0 flex-col items-center gap-2.5 sm:gap-3 outline-none",
        CAT_W,
        "focus-visible:rounded-xl focus-visible:ring-2 focus-visible:ring-primary/35 focus-visible:ring-offset-2",
      )}
      aria-label={`دسته ${category.name}`}
    >
      {/* Transparent frame only — no plate/bg/ring/border */}
      <span
        className={cn(
          "relative grid w-full shrink-0 place-items-center overflow-hidden",
          MARK_H,
        )}
      >
        {fillUrl ? (
          // eslint-disable-next-line @next/next/no-img-element -- category CDN/local icon URLs
          <img
            src={fillUrl}
            alt=""
            className="absolute inset-0 h-full w-full object-cover"
            draggable={false}
          />
        ) : (
          <CategoryVisualIcon
            icon={icon}
            size={28}
            color="#5E5F5E"
            className="pointer-events-none"
          />
        )}
      </span>
      <span
        className={cn(
          "w-full text-center font-semibold leading-snug tracking-tight text-foreground transition-colors group-hover:text-primary",
          /* Long names: wrap up to 2 lines — clip, never ellipsis */
          "break-words line-clamp-2 [text-overflow:clip]",
          longName ? "text-[9.5px] sm:text-[10px]" : "text-[11px]",
        )}
      >
        {category.name}
      </span>
    </Link>
  );
}

function DefaultBrandRow({
  brand,
  logoUrl,
  className,
  animate,
  reduced,
}: {
  brand: BrandBrief;
  logoUrl?: string | null;
  className?: string;
  animate: boolean;
  reduced: boolean;
}) {
  const href = brand.slug?.trim()
    ? `/brands/${brand.slug.trim()}`
    : `/catalog?brand=${brand.id}`;
  const resolved = resolveBrandLogoUrl(brand.name, logoUrl);
  const isSvg = Boolean(resolved?.toLowerCase().includes(".svg"));
  const initial = (brand.name || "B").trim().slice(0, 1);

  const inner = (
    <Link
      href={href}
      className={cn(
        "group inline-flex max-w-full flex-row items-center gap-3.5 outline-none",
        "focus-visible:rounded-xl focus-visible:ring-2 focus-visible:ring-primary/35 focus-visible:ring-offset-2",
        className,
      )}
      aria-label={`برند ${brand.name}`}
    >
      <span
        className={cn(
          "relative grid h-[3.25rem] w-[3.25rem] shrink-0 place-items-center overflow-hidden rounded-xl sm:h-14 sm:w-14",
          plate,
        )}
      >
        {resolved ? (
          <SafeImage
            src={resolved}
            alt=""
            fill
            sizes="56px"
            className="object-contain p-2"
            unoptimized={isSvg}
            fallback={
              <span className="text-lg font-bold text-steel/35">{initial}</span>
            }
          />
        ) : (
          <span className="text-lg font-bold text-steel/35">{initial}</span>
        )}
      </span>
      <span className="min-w-0 text-start">
        <span className="block truncate text-[13px] font-semibold tracking-tight text-foreground transition-colors group-hover:text-primary sm:text-sm">
          {brand.name}
        </span>
        {brand.country ? (
          <span className="mt-0.5 block truncate text-[11px] font-medium text-steel">
            {brand.country}
          </span>
        ) : (
          <span className="mt-0.5 block text-[11px] font-medium text-steel/70">
            صفحه برند
          </span>
        )}
      </span>
    </Link>
  );

  if (!animate || reduced) return inner;

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
    >
      {inner}
    </motion.div>
  );
}

export function findBrandLogoUrl(
  brand: BrandBrief | null | undefined,
  brands: Brand[],
): string | null {
  if (!brand) return null;
  const full = brands.find((b) => b.id === brand.id);
  return resolveBrandLogoUrl(brand.name, full?.logo_url ?? null);
}
