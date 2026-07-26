"use client";

import Link from "next/link";
import Image from "next/image";
import { useMemo } from "react";
import { motion } from "framer-motion";
import * as Icons from "react-iconly";
import { useCategoryTree, useNavGroupDefs } from "@/features/catalog/queries";
import { Skeleton } from "@/components/ui/skeleton";
import {
  categoryHref,
  isMetrologyRoot,
  NAV_GROUPS,
  orderedVisibleRoots,
} from "@/config/nav-groups";
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
  const imageUrl = node.image_url;
  const motionSafe = useMotionSafe();

  return (
    <motion.div
      initial={motionSafe ? { opacity: 0, y: 18 } : false}
      whileInView={motionSafe ? { opacity: 1, y: 0 } : undefined}
      viewport={{ once: true, amount: 0.35 }}
      transition={{ duration: 0.4, delay: Math.min(index * 0.05, 0.35) }}
    >
      <Link
        href={categoryHref(node)}
        className={cn(
          "group flex h-full overflow-hidden rounded-2xl border bg-card shadow-soft transition-all duration-300",
          "hover:-translate-y-1 hover:shadow-glass",
          highlight
            ? "border-primary/30 hover:border-primary/45"
            : "border-border/55 hover:border-steel/35",
        )}
      >
        {/* Visual plane — image never carries overlaid copy */}
        <span
          className={cn(
            "relative block w-[42%] min-w-[7.5rem] shrink-0 self-stretch overflow-hidden sm:w-[46%] sm:min-w-[9rem]",
            highlight ? "bg-primary/5" : "bg-secondary/80",
          )}
        >
          {imageUrl ? (
            <Image
              src={imageUrl}
              alt=""
              fill
              quality={92}
              sizes="(max-width: 640px) 42vw, (max-width: 1024px) 22vw, 180px"
              className="object-cover transition-transform duration-500 group-hover:scale-[1.04]"
              unoptimized
            />
          ) : (
            <span className="grid h-full min-h-[7.5rem] w-full place-items-center">
              <CategoryIcon name={node.icon} />
            </span>
          )}
          <span
            aria-hidden
            className={cn(
              "absolute inset-y-0 end-0 w-px",
              highlight ? "bg-primary/20" : "bg-border/50",
            )}
          />
        </span>

        <span className="flex min-w-0 flex-1 flex-col justify-center gap-1.5 px-4 py-4 sm:px-5 sm:py-5">
          {highlight && (
            <span className="text-[10px] font-bold uppercase tracking-[0.14em] text-primary">
              اولویت کارگاه
            </span>
          )}
          <span className="line-clamp-2 text-sm font-bold leading-6 text-foreground sm:text-base sm:leading-7">
            {node.name}
          </span>
          <span className="text-xs text-steel">
            {formatNumber(node.product_count ?? 0)} محصول
          </span>
          <span className="mt-1 text-xs font-bold text-primary opacity-0 transition-opacity duration-300 group-hover:opacity-100 sm:mt-2">
            ورود به دسته ←
          </span>
        </span>
      </Link>
    </motion.div>
  );
}

/** Ordered L1 roots — static responsive grid (no horizontal scroller). */
export function CategoryGrid() {
  const { data, isLoading } = useCategoryTree();
  const { data: navDefs = NAV_GROUPS } = useNavGroupDefs();
  const roots = useMemo(() => orderedVisibleRoots(data ?? [], navDefs), [data, navDefs]);

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-[120px] w-full rounded-2xl sm:h-[136px]" />
        ))}
      </div>
    );
  }

  if (!roots.length) return null;

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-3">
      {roots.map((node, i) => (
        <CategoryTile key={node.id} node={node} navDefs={navDefs} index={i} />
      ))}
    </div>
  );
}
