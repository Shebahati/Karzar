"use client";

import Link from "next/link";
import { useMemo } from "react";
import { motion } from "framer-motion";
import { ChevronLeft } from "react-iconly";
import { useCategoryTree, useNavGroupDefs } from "@/features/catalog/queries";
import { CategoryVisualIcon } from "@/components/ui/category-visual-icon";
import { Skeleton } from "@/components/ui/skeleton";
import { resolveCategoryIconUrl } from "@/config/category-icons";
import { categoryHref, NAV_GROUPS, orderedTaxonomyRoots } from "@/config/nav-groups";
import { cn, formatNumber } from "@/lib/utils";
import { useMotionSafe } from "@/lib/use-motion-safe";
import type { CategoryTreeNode } from "@/types/category";

const DEFAULT_MAX = 12;

function CategoryOrb({
  node,
  index,
  mode = "link",
  active,
  onSelect,
}: {
  node: CategoryTreeNode;
  index: number;
  mode?: "link" | "toggle";
  active?: boolean;
  onSelect?: (node: CategoryTreeNode) => void;
}) {
  const motionSafe = useMotionSafe();
  const href = categoryHref(node);
  const count = node.product_count ?? 0;

  const inner = (
    <>
      {/* Soft brand wash on hover — no border frame */}
      <span
        aria-hidden
        className={cn(
          "pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-l from-transparent via-primary/40 to-transparent transition-opacity duration-400",
          active ? "opacity-100" : "opacity-0 group-hover:opacity-80",
        )}
      />
      <span
        aria-hidden
        className={cn(
          "pointer-events-none absolute -end-8 -top-8 h-24 w-24 rounded-full bg-primary/[0.05] transition-transform duration-500 group-hover:scale-125",
          active && "bg-primary/15 scale-110",
        )}
      />

      <span
        className={cn(
          "relative grid h-12 w-12 shrink-0 place-items-center overflow-visible rounded-2xl transition-[background-color,transform,box-shadow] duration-400 sm:h-14 sm:w-14",
          active
            ? "bg-primary text-white shadow-[0_12px_28px_-10px_rgba(208,35,39,0.45)]"
            : "bg-primary/[0.08] ring-1 ring-inset ring-primary/10 group-hover:bg-primary/[0.12] group-hover:scale-[1.04]",
        )}
      >
        <CategoryVisualIcon
          icon={resolveCategoryIconUrl(node) ?? node.icon}
          size={30}
          overflowTop
          color={active ? "#FFFFFF" : "#D02327"}
        />
      </span>

      <span className="relative mt-auto min-w-0 space-y-1.5 pt-1">
        <span
          className={cn(
            "block text-[15px] font-black leading-snug tracking-tight sm:text-base",
            active ? "text-primary" : "text-foreground",
          )}
        >
          {node.name}
        </span>
        <span className="flex items-center justify-between gap-2">
          <span
            className={cn(
              "text-[12px] font-bold tabular-nums sm:text-[13px]",
              active ? "text-primary/75" : "text-[#5E5F5E]/75",
            )}
          >
            {formatNumber(count)} محصول
          </span>
          {mode === "link" ? (
            <span
              aria-hidden
              className={cn(
                "grid h-7 w-7 place-items-center rounded-full transition-all duration-300",
                "text-[#5E5F5E]/50 group-hover:bg-primary group-hover:text-white group-hover:opacity-100",
                "opacity-0 translate-x-1 group-hover:translate-x-0 group-hover:opacity-100",
              )}
            >
              <ChevronLeft size="small" set="bold" primaryColor="currentColor" />
            </span>
          ) : null}
        </span>
      </span>
    </>
  );

  const shell = cn(
    "group relative flex h-full min-h-[9.5rem] flex-col overflow-hidden rounded-[1.35rem] p-5 outline-none sm:min-h-[10.5rem] sm:p-6",
    "transition-[transform,box-shadow,background-color] duration-400 ease-out",
    "focus-visible:ring-2 focus-visible:ring-primary/35 focus-visible:ring-offset-2",
    active
      ? "bg-white shadow-[0_1px_0_rgba(94,95,94,0.06),0_18px_40px_-18px_rgba(208,35,39,0.28)] ring-1 ring-primary/20"
      : [
          "bg-[#F5F5F5]",
          "shadow-[0_1px_0_rgba(94,95,94,0.05),0_10px_28px_-20px_rgba(94,95,94,0.22)]",
          "hover:-translate-y-0.5 hover:bg-white",
          "hover:shadow-[0_1px_0_rgba(94,95,94,0.06),0_18px_36px_-16px_rgba(208,35,39,0.16)]",
        ].join(" "),
  );

  return (
    <motion.div
      initial={motionSafe ? { opacity: 0, y: 20 } : false}
      whileInView={motionSafe ? { opacity: 1, y: 0 } : undefined}
      viewport={{ once: true, amount: 0.2 }}
      transition={{
        duration: 0.45,
        delay: Math.min(index * 0.045, 0.4),
        ease: [0.22, 1, 0.36, 1],
      }}
      className="h-full"
    >
      {mode === "toggle" ? (
        <button type="button" aria-pressed={active} onClick={() => onSelect?.(node)} className={shell}>
          {inner}
        </button>
      ) : (
        <Link href={href} className={shell}>
          {inner}
        </Link>
      )}
    </motion.div>
  );
}

function TileSkeleton() {
  return (
    <div className="flex min-h-[9.5rem] flex-col rounded-[1.35rem] bg-[#F5F5F5] p-5 sm:min-h-[10.5rem] sm:p-6">
      <Skeleton className="h-12 w-12 rounded-2xl sm:h-14 sm:w-14" />
      <div className="mt-auto space-y-2 pt-6">
        <Skeleton className="h-4 w-[70%] rounded-full" />
        <Skeleton className="h-3 w-16 rounded-full" />
      </div>
    </div>
  );
}

/**
 * Desktop L1 category grid — live category tree (admin categories).
 * Premium tile layout for md+ home; mobile uses MobileCategorySection.
 * Prefers RSC-passed `initialTree` so SSR HTML matches hydrated client
 * (avoids shimmer ↔ Link hydration mismatch, same pattern as BrandStrip).
 */
export function CategoryOrbsGrid({
  mode = "link",
  selectedIds,
  onToggle,
  className,
  maxItems = DEFAULT_MAX,
  columns,
  initialTree = [],
}: {
  mode?: "link" | "toggle";
  selectedIds?: number[];
  onToggle?: (node: CategoryTreeNode) => void;
  className?: string;
  /** Cap L1 roots (default 12) */
  maxItems?: number;
  /** Force column count; default responsive 3 / 4 */
  columns?: 2 | 3 | 4;
  /** RSC prefetch seed — keeps first paint stable across hydrate. */
  initialTree?: CategoryTreeNode[];
}) {
  const { data, isLoading } = useCategoryTree();
  const { data: navDefs = NAV_GROUPS } = useNavGroupDefs();
  const tree = useMemo(
    () => (data?.length ? data : initialTree) ?? [],
    [data, initialTree],
  );
  const roots = useMemo(() => {
    const all = orderedTaxonomyRoots(tree, navDefs);
    return maxItems != null ? all.slice(0, maxItems) : all;
  }, [tree, navDefs, maxItems]);

  const gridClass =
    columns === 2
      ? "grid-cols-2 gap-4"
      : columns === 3
        ? "grid-cols-3 gap-4 sm:gap-5"
        : columns === 4
          ? "grid-cols-4 gap-4 sm:gap-5"
          : "grid-cols-3 gap-4 sm:gap-5 lg:grid-cols-4 lg:gap-5";

  const skeletonCount = maxItems ?? 12;
  // Only shimmer when we have neither query data nor RSC seed (true cold load).
  const waiting = isLoading && tree.length === 0;

  if (waiting) {
    return (
      <div className={cn("grid", gridClass, className)}>
        {Array.from({ length: skeletonCount }).map((_, i) => (
          <TileSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (!roots.length) return null;

  return (
    <div className={cn("grid", gridClass, className)}>
      {roots.map((node, i) => (
        <CategoryOrb
          key={node.id}
          node={node}
          index={i}
          mode={mode}
          active={selectedIds?.includes(node.id)}
          onSelect={onToggle}
        />
      ))}
    </div>
  );
}
