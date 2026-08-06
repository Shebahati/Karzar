"use client";

import Link from "next/link";
import { useMemo } from "react";
import { ChevronLeft } from "react-iconly";
import {
  MobileCategoryCard,
  MobileCategoryCardSkeleton,
} from "@/components/category/mobile-category-card";
import { useCategoryTree, useNavGroupDefs } from "@/features/catalog/queries";
import { resolveCategoryIconUrl } from "@/config/category-icons";
import { categoryHref, NAV_GROUPS, orderedTaxonomyRoots } from "@/config/nav-groups";
import { cn } from "@/lib/utils";
import type { CategoryTreeNode } from "@/types/category";

/** Live L1 count is API-driven; skeleton placeholder count only. */
const SKELETON_L1 = 13;

/**
 * Mobile-only L1 category section for the home page.
 * Same soft-industrial card chrome as `/categories` — 2-col grid layout unchanged.
 */
export function MobileCategorySection({
  className,
  initialTree = [],
}: {
  className?: string;
  /** RSC prefetch seed — stable SSR/client first paint. */
  initialTree?: CategoryTreeNode[];
}) {
  const { data, isLoading } = useCategoryTree();
  const { data: navDefs = NAV_GROUPS } = useNavGroupDefs();

  const tree = useMemo(
    () => (data?.length ? data : initialTree) ?? [],
    [data, initialTree],
  );
  const roots = useMemo(() => orderedTaxonomyRoots(tree, navDefs), [tree, navDefs]);

  const waiting = isLoading && tree.length === 0;

  return (
    <section
      aria-labelledby="home-mobile-categories-heading"
      className={cn("relative max-w-full overflow-x-clip md:hidden", className)}
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 -top-4 bottom-0 -z-10 overflow-hidden"
      >
        <div className="absolute inset-0 bg-gradient-to-b from-[#F0F0F1] via-[#F5F5F6]/85 to-transparent" />
        <div className="absolute start-[12%] top-6 h-36 w-36 rounded-full bg-[radial-gradient(circle,rgba(94,95,94,0.07)_0%,transparent_70%)]" />
        <div className="absolute end-[8%] top-16 h-28 w-40 rounded-full bg-[radial-gradient(ellipse,rgba(208,35,39,0.04)_0%,transparent_72%)]" />
      </div>

      <div className="mb-4 flex items-end justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2.5">
            <span
              className="h-6 w-1.5 shrink-0 rounded-full bg-gradient-to-b from-[#D02327] via-[#D02327] to-[#D02327]/35 shadow-[0_4px_10px_-4px_rgba(208,35,39,0.55)]"
              aria-hidden
            />
            <h2
              id="home-mobile-categories-heading"
              className="type-section tracking-tight text-foreground"
            >
              دسته‌بندی محصولات
            </h2>
          </div>
          <p className="type-lede mt-1.5 ps-4 text-muted-foreground">
            انتخاب سریع از دسته‌های اصلی
          </p>
        </div>

        <Link
          href="/catalog"
          className={cn(
            "group flex shrink-0 items-center gap-0.5 rounded-full pb-0.5",
            "px-2.5 py-1 text-xs font-bold text-primary",
            "bg-primary/[0.06] ring-1 ring-inset ring-primary/10",
            "transition-[background-color,ring-color] duration-200",
            "hover:bg-primary/[0.1] hover:ring-primary/18",
            "active:scale-[0.97]",
          )}
        >
          همه
          <ChevronLeft size="small" set="light" />
        </Link>
      </div>

      {waiting ? (
        <div className="grid grid-cols-2 gap-3">
          {Array.from({ length: SKELETON_L1 }).map((_, i) => (
            <MobileCategoryCardSkeleton key={i} />
          ))}
        </div>
      ) : roots.length === 0 ? null : (
        <div className="grid grid-cols-2 gap-3">
          {roots.map((node) => (
            <MobileCategoryCard
              key={node.id}
              name={node.name}
              href={categoryHref(node)}
              icon={resolveCategoryIconUrl(node) ?? node.icon}
              count={node.product_count ?? 0}
            />
          ))}
        </div>
      )}
    </section>
  );
}
