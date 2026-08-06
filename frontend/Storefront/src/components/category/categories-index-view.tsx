"use client";

import { useMemo } from "react";
import Link from "next/link";
import { Category, ChevronLeft } from "react-iconly";
import {
  MobileCategoryCard,
  MobileCategoryCardSkeleton,
} from "@/components/category/mobile-category-card";
import { Container } from "@/components/ui/container";
import {
  CATEGORY_ICON_BY_SLUG,
  resolveCategoryIconUrl,
} from "@/config/category-icons";
import { FINAL_L1_CATEGORIES } from "@/config/l1-categories";
import { categoryHref } from "@/config/nav-groups";
import { useCategoryTree } from "@/features/catalog/queries";
import type { CategoryTreeNode } from "@/types/category";

function normalize(s: string): string {
  return s
    .trim()
    .replace(/\u200c/g, "")
    .replace(/ي/g, "ی")
    .replace(/ك/g, "ک")
    .toLowerCase();
}

function findLiveRoot(
  tree: CategoryTreeNode[],
  name: string,
  aliases: string[],
  slug: string,
): CategoryTreeNode | undefined {
  const names = new Set([name, ...aliases].map(normalize));
  const slugN = normalize(slug);
  return tree.find((r) => {
    const n = normalize(r.name);
    const s = normalize(r.slug ?? "");
    return (
      names.has(n) ||
      aliases.some((a) => n.includes(normalize(a))) ||
      (s.length > 0 && (s === slugN || s.includes(slugN) || slugN.includes(s)))
    );
  });
}

type CategoryCard = {
  key: string;
  name: string;
  href: string;
  icon: string | null;
  count: number | null;
};

/**
 * Dedicated L1 categories screen for bottom-nav «محصولات».
 * Canonical 12 L1 + designed category-icons — not an overlay sheet.
 */
export function CategoriesIndexView() {
  const { data: tree = [], isLoading } = useCategoryTree();

  const cards = useMemo<CategoryCard[]>(() => {
    return FINAL_L1_CATEGORIES.map((c) => {
      const live = findLiveRoot(tree, c.name, c.aliases, c.slug);
      const icon =
        CATEGORY_ICON_BY_SLUG[c.iconSlug] ??
        CATEGORY_ICON_BY_SLUG[c.slug] ??
        (live ? resolveCategoryIconUrl(live) : null) ??
        resolveCategoryIconUrl({ name: c.name, slug: c.slug });
      return {
        key: c.key,
        name: c.name,
        href: live ? categoryHref(live) : `/categories/${c.slug}`,
        icon,
        count: live?.product_count ?? null,
      };
    });
  }, [tree]);

  const waiting = isLoading && tree.length === 0;

  return (
    <div className="relative min-h-[60vh] overflow-hidden bg-background">
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute inset-0 bg-gradient-to-b from-[#F7F7F7] via-background to-background" />
        <div className="absolute -start-24 top-10 h-56 w-56 rounded-full bg-primary/[0.05] blur-3xl" />
        <div className="absolute -end-16 top-40 h-44 w-44 rounded-full bg-[#5E5F5E]/[0.06] blur-3xl" />
      </div>

      <Container className="py-6 sm:py-8 lg:py-10">
        <header className="mb-6 sm:mb-8">
          <div className="flex items-center gap-3">
            <span className="grid h-11 w-11 place-items-center rounded-2xl bg-primary/[0.08] text-primary ring-1 ring-inset ring-primary/10">
              <Category set="bold" size="medium" primaryColor="currentColor" />
            </span>
            <div className="min-w-0">
              <h1 className="type-section text-foreground">محصولات</h1>
              <p className="type-lede mt-1 text-muted-foreground">
                ۱۲ دستهٔ اصلی ابزار صنعتی کارزار
              </p>
            </div>
          </div>

          <Link
            href="/catalog"
            className="mt-4 inline-flex items-center gap-0.5 text-xs font-bold text-primary"
          >
            مشاهده همه محصولات
            <ChevronLeft size="small" set="light" />
          </Link>
        </header>

        {waiting ? (
          <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 12 }).map((_, i) => (
              <MobileCategoryCardSkeleton key={i} />
            ))}
          </div>
        ) : (
          <ul className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 sm:gap-3 lg:grid-cols-3 lg:gap-3.5">
            {cards.map((card) => (
              <li key={card.key}>
                <MobileCategoryCard
                  name={card.name}
                  href={card.href}
                  icon={card.icon}
                  count={card.count}
                  showChevron
                />
              </li>
            ))}
          </ul>
        )}
      </Container>
    </div>
  );
}
