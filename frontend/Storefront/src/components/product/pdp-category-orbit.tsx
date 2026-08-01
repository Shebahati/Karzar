"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { CategoryVisualIcon } from "@/components/ui/category-visual-icon";
import { resolveCategoryIconUrl } from "@/config/category-icons";
import { categoryHref } from "@/config/nav-groups";
import { cn } from "@/lib/utils";
import type { CategoryFlat } from "@/types/category";

/**
 * Single L1 category orbit for PDP — same visual language as hero MaterialOrb,
 * placed as a navigational anchor (not a sticker dump).
 */
export function PdpCategoryOrbit({
  category,
  className,
  size = "md",
  animate = true,
}: {
  category: Pick<CategoryFlat, "id" | "name" | "slug" | "icon" | "image_url">;
  className?: string;
  size?: "sm" | "md";
  animate?: boolean;
}) {
  const reduced = useReducedMotion();
  const icon =
    resolveCategoryIconUrl({
      name: category.name,
      slug: category.slug,
      icon: category.icon,
      image_url: category.image_url,
    }) ?? category.icon;

  const disc =
    size === "sm"
      ? "h-12 w-12 sm:h-14 sm:w-14"
      : "h-14 w-14 sm:h-[3.85rem] sm:w-[3.85rem]";
  const iconSize = size === "sm" ? 26 : 30;
  const overflowScale = 2.35;

  const body = (
    <>
      <span
        className={cn(
          "relative flex items-center justify-center overflow-visible rounded-full",
          "bg-white/90 shadow-[0_8px_22px_rgba(94,95,94,0.18)] ring-1 ring-white/70",
          "transition-[transform,box-shadow,background-color] duration-300",
          "group-hover:scale-[1.05] group-hover:bg-white group-hover:shadow-[0_12px_28px_rgba(208,35,39,0.18)]",
          disc,
        )}
      >
        <CategoryVisualIcon
          icon={icon}
          size={iconSize}
          overflowTop
          overflowScale={overflowScale}
          imgClassName="-translate-y-[6%] drop-shadow-[0_6px_12px_rgba(0,0,0,0.22)]"
          color="#5E5F5E"
        />
      </span>
      <span className="mt-2 max-w-[5.5rem] text-center text-[10px] font-semibold leading-snug tracking-tight text-steel sm:max-w-[6.25rem] sm:text-[11px]">
        {category.name}
      </span>
    </>
  );

  const shell = cn(
    "group flex shrink-0 flex-col items-center outline-none",
    "focus-visible:rounded-2xl focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-primary/40",
    className,
  );

  const link = (
    <Link
      href={categoryHref(category)}
      className={shell}
      aria-label={`دسته ${category.name}`}
    >
      {body}
    </Link>
  );

  if (!animate || reduced) return link;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.94 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1], delay: 0.12 }}
    >
      {link}
    </motion.div>
  );
}

/** Resolve the product’s primary (L1 / root) category from flat taxonomy. */
export function resolveProductL1Category(
  productCategory: {
    id?: number | null;
    ancestor_ids?: number[];
  } | null,
  categories: CategoryFlat[],
): CategoryFlat | null {
  if (!productCategory?.id && !productCategory?.ancestor_ids?.length) return null;
  const byId = new Map(categories.map((c) => [c.id, c]));

  const fromAncestors = productCategory.ancestor_ids?.[0];
  if (fromAncestors != null) {
    const root = byId.get(fromAncestors);
    if (root) return root;
  }

  const leaf = productCategory.id != null ? byId.get(productCategory.id) : undefined;
  if (!leaf) return null;

  if (leaf.parent_id == null || leaf.depth === 1) return leaf;
  const rootId = leaf.ancestor_ids?.[0];
  return rootId != null ? (byId.get(rootId) ?? null) : null;
}
