"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { ChevronLeft } from "react-iconly";
import { useCategoryTree, useNavGroupDefs } from "@/features/catalog/queries";
import { CategoryVisualIcon } from "@/components/ui/category-visual-icon";
import { Skeleton } from "@/components/ui/skeleton";
import { resolveCategoryIconUrl } from "@/config/category-icons";
import { categoryHref, NAV_GROUPS, orderedTaxonomyRoots } from "@/config/nav-groups";
import { cn, formatNumber } from "@/lib/utils";
import type { CategoryTreeNode } from "@/types/category";

const MAX_L1 = 12;

function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReduced(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);
  return reduced;
}

function CategoryTile({
  node,
  index,
  reduceMotion,
}: {
  node: CategoryTreeNode;
  index: number;
  reduceMotion: boolean;
}) {
  const count = node.product_count ?? 0;

  return (
    <motion.div
      initial={reduceMotion ? false : { opacity: 0, y: 14 }}
      whileInView={reduceMotion ? undefined : { opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.2 }}
      transition={
        reduceMotion
          ? undefined
          : {
              duration: 0.4,
              delay: Math.min(index * 0.04, 0.36),
              ease: [0.22, 1, 0.36, 1],
            }
      }
    >
      <Link
        href={categoryHref(node)}
        className={cn(
          "group relative flex min-h-[4.5rem] items-center gap-3 overflow-hidden rounded-2xl",
          "bg-[#F4F4F4]/px-3 py-3",
          "transition-[transform,background-color,box-shadow] duration-300 ease-out",
          "active:scale-[0.98]",
          "hover:bg-[#EFEFEF]",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/35 focus-visible:ring-offset-2",
        )}
      >
        <span
          aria-hidden
          className="pointer-events-none absolute inset-y-0 start-0 w-0.5 bg-gradient-to-b from-transparent via-primary/50 to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        />

        <span
          className={cn(
            "relative grid h-11 w-11 shrink-0 place-items-center overflow-visible rounded-full bg-white",
            "shadow-[0_4px_14px_-6px_rgba(94,95,94,0.35)]",
            "transition-transform duration-300 ease-out group-hover:scale-105",
            "group-hover:shadow-[0_8px_18px_-8px_rgba(208,35,39,0.28)]",
          )}
        >
          <CategoryVisualIcon
            icon={resolveCategoryIconUrl(node) ?? node.icon}
            size={26}
            overflowTop
            color="#5E5F5E"
          />
        </span>

        <span className="min-w-0 flex-1 text-start">
          <span className="block text-[13px] font-black leading-snug tracking-tight text-foreground line-clamp-2">
            {node.name}
          </span>
          <span className="mt-1 block text-[11px] font-bold text-[#5E5F5E]/70">
            {formatNumber(count)} محصول
          </span>
        </span>
      </Link>
    </motion.div>
  );
}

function TileSkeleton() {
  return (
    <div className="flex min-h-[4.5rem] items-center gap-3 rounded-2xl bg-[#F4F4F4] px-3 py-3">
      <Skeleton className="h-11 w-11 shrink-0 rounded-full" />
      <div className="min-w-0 flex-1 space-y-2">
        <Skeleton className="h-3.5 w-[72%] rounded-full" />
        <Skeleton className="h-2.5 w-14 rounded-full" />
      </div>
    </div>
  );
}

/**
 * Mobile-only L1 category section for the home page.
 * 2-column readable tiles — avoids cramped 3×4 orb rows.
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
  const reduceMotion = usePrefersReducedMotion();

  const tree = useMemo(
    () => (data?.length ? data : initialTree) ?? [],
    [data, initialTree],
  );
  const roots = useMemo(() => {
    const all = orderedTaxonomyRoots(tree, navDefs);
    return all.slice(0, MAX_L1);
  }, [tree, navDefs]);

  const waiting = isLoading && tree.length === 0;

  return (
    <section
      aria-labelledby="home-mobile-categories-heading"
      className={cn("relative md:hidden", className)}
    >
      <div
        aria-hidden
        className="pointer-events-none absolute -inset-x-5 -top-2 bottom-0 -z-10 overflow-hidden"
      >
        <div className="absolute inset-0 bg-gradient-to-b from-[#F8F8F8] via-transparent to-transparent" />
        <div className="absolute -start-16 top-8 h-40 w-40 rounded-full bg-primary/[0.04] blur-3xl" />
        <div className="absolute -end-10 top-24 h-32 w-32 rounded-full bg-[#5E5F5E]/[0.05] blur-3xl" />
      </div>

      <div className="mb-4 flex items-end justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2.5">
            <span className="h-6 w-1.5 shrink-0 rounded-full bg-primary" aria-hidden />
            <h2
              id="home-mobile-categories-heading"
              className="type-section text-foreground"
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
          className="group flex shrink-0 items-center gap-0.5 pb-0.5 text-xs font-bold text-primary"
        >
          همه
          <ChevronLeft size="small" set="light" />
        </Link>
      </div>

      {waiting ? (
        <div className="grid grid-cols-2 gap-2.5">
          {Array.from({ length: MAX_L1 }).map((_, i) => (
            <TileSkeleton key={i} />
          ))}
        </div>
      ) : roots.length === 0 ? null : (
        <div className="grid grid-cols-2 gap-2.5">
          {roots.map((node, i) => (
            <CategoryTile
              key={node.id}
              node={node}
              index={i}
              reduceMotion={reduceMotion}
            />
          ))}
        </div>
      )}
    </section>
  );
}
