"use client";

import Link from "next/link";
import { useMemo } from "react";
import { motion } from "framer-motion";
import * as Icons from "react-iconly";
import { ChevronLeft } from "react-iconly";
import { useCategoryTree, useNavGroupDefs } from "@/features/catalog/queries";
import { SafeImage } from "@/components/ui/safe-image";
import { Skeleton } from "@/components/ui/skeleton";
import {
  categoryHref,
  isMetrologyRoot,
  NAV_GROUPS,
  orderedTaxonomyRoots,
} from "@/config/nav-groups";
import { CONTENT_IMAGE_QUALITY } from "@/lib/cwv";
import { resolveCategoryImage } from "@/lib/category-images";
import { cn, formatNumber } from "@/lib/utils";
import { useMotionSafe } from "@/lib/use-motion-safe";
import type { CategoryTreeNode } from "@/types/category";

function CategoryIcon({ name }: { name?: string }) {
  const Cmp = (name && (Icons as Record<string, unknown>)[name]) || Icons.Category;
  const Icon = Cmp as typeof Icons.Category;
  return <Icon size="large" set="bold" primaryColor="#5E5F5E" />;
}

function CategoryTile({
  node,
  navDefs,
  index,
}: {
  node: CategoryTreeNode;
  navDefs: typeof NAV_GROUPS;
  index: number;
}) {
  const highlight = isMetrologyRoot(node, navDefs);
  const imageUrl = resolveCategoryImage(node);
  const motionSafe = useMotionSafe();

  return (
    <motion.div
      initial={motionSafe ? { opacity: 0, y: 22 } : false}
      whileInView={motionSafe ? { opacity: 1, y: 0 } : undefined}
      viewport={{ once: true, amount: 0.3 }}
      transition={{ duration: 0.45, delay: Math.min(index * 0.04, 0.32), ease: "easeOut" }}
    >
      <Link
        href={categoryHref(node)}
        className={cn(
          "group flex h-full flex-col overflow-hidden rounded-2xl border bg-card shadow-soft transition-all duration-300",
          "hover:-translate-y-1 hover:shadow-glass",
          highlight
            ? "border-primary/30 hover:border-primary/45"
            : "border-border/55 hover:border-steel/35",
        )}
      >
        {/* Full-bleed visual plane — no text overlay on the photo */}
        <span
          className={cn(
            "relative block aspect-[4/3] w-full overflow-hidden sm:aspect-[5/4]",
            highlight ? "bg-primary/5" : "bg-secondary/80",
          )}
        >
          {imageUrl ? (
            <SafeImage
              src={imageUrl}
              alt=""
              fill
              quality={CONTENT_IMAGE_QUALITY}
              sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
              className="object-cover transition-transform duration-700 ease-out group-hover:scale-[1.06]"
              unoptimized={imageUrl.startsWith("http")}
              fallback={
                <span className="grid h-full w-full place-items-center">
                  <CategoryIcon name={node.icon} />
                </span>
              }
            />
          ) : (
            <span className="grid h-full w-full place-items-center">
              <CategoryIcon name={node.icon} />
            </span>
          )}
          <span
            aria-hidden
            className="pointer-events-none absolute inset-x-0 bottom-0 h-10 bg-gradient-to-t from-black/15 to-transparent"
          />
        </span>

        <span className="flex min-w-0 flex-1 flex-col gap-1 px-4 py-3.5 sm:px-5 sm:py-4">
          {highlight && (
            <span className="text-[10px] font-bold tracking-normal text-primary">اولویت کارگاه</span>
          )}
          <span className="line-clamp-2 text-sm font-bold leading-6 text-foreground sm:text-base sm:leading-7">
            {node.name}
          </span>
          <span className="flex items-center justify-between gap-2 text-xs text-steel">
            <span>{formatNumber(node.product_count ?? 0)} محصول</span>
            <span className="flex items-center gap-0.5 font-bold text-primary opacity-0 transition-opacity duration-300 group-hover:opacity-100">
              ورود
              <ChevronLeft size="small" set="light" primaryColor="#D02327" />
            </span>
          </span>
        </span>
      </Link>
    </motion.div>
  );
}

/** Ordered L1 roots — full-bleed image tiles with label band below. */
export function CategoryGrid() {
  const { data, isLoading } = useCategoryTree();
  const { data: navDefs = NAV_GROUPS } = useNavGroupDefs();
  const roots = useMemo(() => orderedTaxonomyRoots(data ?? [], navDefs), [data, navDefs]);

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-5 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="aspect-[4/3] w-full rounded-2xl sm:min-h-[280px]" />
        ))}
      </div>
    );
  }

  if (!roots.length) return null;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-5 lg:grid-cols-3">
      {roots.map((node, i) => (
        <CategoryTile key={node.id} node={node} navDefs={navDefs} index={i} />
      ))}
    </div>
  );
}
