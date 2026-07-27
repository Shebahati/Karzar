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
import { CONTENT_IMAGE_QUALITY } from "@/lib/cwv";
import { cn, formatNumber } from "@/lib/utils";
import { useMotionSafe } from "@/lib/use-motion-safe";
import type { CategoryTreeNode } from "@/types/category";

/** Curated local art — preferred over API packshots for homepage tiles. */
const CURATED_BY_ID: Record<number, string> = {
  1: "/images/categories/toolholding.jpg",
  2: "/images/categories/insert-tools.jpg",
  4: "/images/categories/endmills.jpg",
  5: "/images/categories/drills.jpg",
  6: "/images/categories/taps.jpg",
  8: "/images/categories/workholding.jpg",
  9: "/images/categories/machines.jpg",
  56: "/images/categories/metrology-precision.jpg",
  81: "/images/categories/metrology-cnc.jpg",
  87: "/images/categories/metrology-lab.jpg",
  154: "/images/categories/accessories.jpg",
  165: "/images/categories/inserts.jpg",
};

const CURATED_BY_NAME: Record<string, string> = {
  ابزارگیر: CURATED_BY_ID[1],
  "ابزار اینسرتی": CURATED_BY_ID[2],
  اینسرت: CURATED_BY_ID[165],
  "ابزار انگشتی": CURATED_BY_ID[4],
  مته: CURATED_BY_ID[5],
  قلاویز: CURATED_BY_ID[6],
  "ابزار گیرشی": CURATED_BY_ID[8],
  "دستگاه‌های صنعتی": CURATED_BY_ID[9],
  "دستگاه های صنعتی": CURATED_BY_ID[9],
  "اندازه گیری دقیق": CURATED_BY_ID[56],
  "اندازه‌گیری دقیق": CURATED_BY_ID[56],
  "CNC اندازه گیری": CURATED_BY_ID[81],
  "اندازه گیری آزمایشگاهی": CURATED_BY_ID[87],
  "لوازم جانبی صنعتی": CURATED_BY_ID[154],
};

function normalizeName(name: string): string {
  return name.trim().replace(/\u200c/g, "").replace(/ي/g, "ی").replace(/ك/g, "ک");
}

function resolveCategoryImage(node: CategoryTreeNode): string | null {
  if (CURATED_BY_ID[node.id]) return CURATED_BY_ID[node.id];
  const byName = CURATED_BY_NAME[normalizeName(node.name)];
  if (byName) return byName;
  return node.image_url ?? null;
}

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
            <Image
              src={imageUrl}
              alt=""
              fill
              quality={CONTENT_IMAGE_QUALITY}
              sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
              className="object-cover transition-transform duration-700 ease-out group-hover:scale-[1.06]"
              unoptimized={imageUrl.startsWith("http")}
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
            <span className="text-[10px] font-bold tracking-[0.12em] text-primary">اولویت کارگاه</span>
          )}
          <span className="line-clamp-2 text-sm font-bold leading-6 text-foreground sm:text-base sm:leading-7">
            {node.name}
          </span>
          <span className="flex items-center justify-between gap-2 text-xs text-steel">
            <span>{formatNumber(node.product_count ?? 0)} محصول</span>
            <span className="font-bold text-primary opacity-0 transition-opacity duration-300 group-hover:opacity-100">
              ورود ←
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
  const roots = useMemo(() => orderedVisibleRoots(data ?? [], navDefs), [data, navDefs]);

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
