"use client";

import { useMemo } from "react";
import { ProductCarousel } from "@/components/home/product-carousel";
import { SectionHeading } from "@/components/home/section-heading";
import { FINAL_L1_CATEGORIES } from "@/config/l1-categories";
import { categoryHref } from "@/config/nav-groups";
import { useProducts } from "@/features/catalog/queries";
import type { CategoryCarouselSection } from "@/types/home-layout";
import type { CategoryTreeNode } from "@/types/category";

function normalizeFa(s: string): string {
  return s.trim().replace(/\u200c/g, "").replace(/ي/g, "ی").replace(/ك/g, "ک").toLowerCase();
}

function findNodeById(
  nodes: CategoryTreeNode[],
  id: number,
): CategoryTreeNode | undefined {
  for (const node of nodes) {
    if (node.id === id) return node;
    const child = findNodeById(node.subcategories ?? [], id);
    if (child) return child;
  }
  return undefined;
}

/** Resolve category via id, else slug + FINAL_L1 aliases (legacy defaults). */
function resolveCategory(
  tree: CategoryTreeNode[],
  section: CategoryCarouselSection,
): CategoryTreeNode | undefined {
  if (section.categoryId > 0) {
    const byId = findNodeById(tree, section.categoryId);
    if (byId) return byId;
  }

  const slug = section.categorySlug?.trim();
  if (!slug) return undefined;

  const def = FINAL_L1_CATEGORIES.find((c) => c.slug === slug);
  const slugN = normalizeFa(slug);
  const names = new Set(
    [def?.name, ...(def?.aliases ?? []), section.title]
      .filter(Boolean)
      .map((n) => normalizeFa(n!)),
  );

  const walk = (nodes: CategoryTreeNode[]): CategoryTreeNode | undefined => {
    for (const node of nodes) {
      const nameN = normalizeFa(node.name);
      const nodeSlug = normalizeFa(node.slug ?? "");
      if (
        nodeSlug === slugN ||
        names.has(nameN) ||
        (nodeSlug.length > 0 &&
          (nodeSlug.includes(slugN) || slugN.includes(nodeSlug)))
      ) {
        return node;
      }
      const child = walk(node.subcategories ?? []);
      if (child) return child;
    }
    return undefined;
  };

  return walk(tree);
}

export function HomeCategoryCarousel({
  section,
  tree,
}: {
  section: CategoryCarouselSection;
  tree: CategoryTreeNode[];
}) {
  const root = useMemo(() => resolveCategory(tree, section), [tree, section]);
  const limit = section.limit && section.limit > 0 ? section.limit : 12;

  const catalog = useProducts({
    limit,
    sort: "newest",
    // 0 until resolved — never accidentally list full catalog.
    category_id: root?.id ?? 0,
  });

  const products = catalog.data?.data ?? [];
  if (!root) return null;
  if (!catalog.isLoading && products.length === 0) return null;

  return (
    <section>
      <SectionHeading
        title={section.title || root.name}
        subtitle={section.subtitle}
        href={categoryHref(root)}
        hrefLabel={section.ctaLabel || "مشاهده همه"}
      />
      <ProductCarousel
        products={products}
        isLoading={catalog.isLoading}
        variant="featured"
      />
    </section>
  );
}
