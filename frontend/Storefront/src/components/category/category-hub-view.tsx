"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { ChevronLeft } from "react-iconly";
import { Container } from "@/components/ui/container";
import { CatalogView } from "@/components/catalog/catalog-view";
import { RootCategoryCarousel } from "@/components/catalog/root-category-carousel";
import { CategoryHubIntro } from "@/components/category/category-hub-intro";
import { HubChildNav } from "@/components/category/hub-child-nav";
import { useFlatCategories } from "@/features/catalog/queries";
import { categoryHref } from "@/config/nav-groups";
import type { HubIntro } from "@/lib/hub-intros";
import type { CategoryFlat, CategoryTreeNode } from "@/types/category";

/** Preserve first-seen order; drop duplicate ancestor ids from L1 promote/seed quirks. */
function uniqueIds(ids: number[]): number[] {
  const seen = new Set<number>();
  const out: number[] = [];
  for (const id of ids) {
    if (seen.has(id)) continue;
    seen.add(id);
    out.push(id);
  }
  return out;
}

export function CategoryHubView({
  category,
  intro = null,
  initialTree = [],
  initialFlat = [],
}: {
  category: CategoryFlat;
  intro?: HubIntro | null;
  /** RSC prefetch seed for L1 carousel (avoids skeleton ↔ orbs hydration mismatch). */
  initialTree?: CategoryTreeNode[];
  /** RSC prefetch seed for breadcrumbs / child nav. */
  initialFlat?: CategoryFlat[];
}) {
  const { data } = useFlatCategories();
  const all = useMemo(
    () => (data?.length ? data : initialFlat) ?? [],
    [data, initialFlat],
  );
  const byId = useMemo(() => new Map(all.map((c) => [c.id, c])), [all]);
  const pathIds = uniqueIds([...(category.ancestor_ids ?? []), category.id]);
  const crumbs = pathIds
    .map((id) => byId.get(id))
    .filter((c): c is CategoryFlat => Boolean(c));
  const children = all
    .filter((c) => c.parent_id === category.id)
    .sort((a, b) => (b.product_count ?? 0) - (a.product_count ?? 0));
  const showStandaloneChildNav = !intro && children.length > 0;

  const fallbackDescription =
    category.meta_description ||
    (category.breadcrumb?.length
      ? `محصولات دسته «${category.breadcrumb.join(" › ")}» در فروشگاه کارزار.`
      : null);

  return (
    <>
      <Container className="pt-3 pb-1 lg:pt-6 lg:pb-2">
        <nav
          aria-label="breadcrumb"
          className="mb-3 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground lg:mb-5"
        >
          <Link href="/" className="hover:text-primary">
            خانه
          </Link>
          <ChevronLeft size="small" set="light" />
          <Link href="/catalog" className="hover:text-primary">
            فروشگاه
          </Link>
          {crumbs.map((crumb) => (
            <span key={crumb.id} className="flex items-center gap-1.5">
              <ChevronLeft size="small" set="light" />
              {crumb.id === category.id ? (
                <span className="font-bold text-foreground">{crumb.name}</span>
              ) : (
                <Link href={categoryHref(crumb)} className="hover:text-primary">
                  {crumb.name}
                </Link>
              )}
            </span>
          ))}
        </nav>

        <div className="mb-1 lg:mb-2">
          <RootCategoryCarousel
            lockedCategoryId={category.id}
            initialTree={initialTree}
          />
        </div>

        {showStandaloneChildNav ? (
          <div className="mt-2 lg:mt-4">
            <HubChildNav childCategories={children} hubName={category.name} />
          </div>
        ) : null}
      </Container>

      <CatalogView lockedCategoryId={category.id} initialTree={initialTree} />

      {(intro || fallbackDescription) && (
        <Container className="pb-12 pt-4">
          {intro ? (
            <CategoryHubIntro intro={intro} childCategories={children} collapsible />
          ) : (
            <CollapsiblePlainText text={fallbackDescription!} title={category.name} />
          )}
        </Container>
      )}
    </>
  );
}

function CollapsiblePlainText({ text, title }: { text: string; title: string }) {
  const [expanded, setExpanded] = useState(false);
  const needsMore = text.length > 280;
  const shown = !needsMore || expanded ? text : `${text.slice(0, 280).trimEnd()}…`;

  return (
    <section className="max-w-3xl" aria-label={`معرفی دسته ${title}`} dir="rtl">
      <p className="text-sm leading-8 text-foreground/90 sm:text-[15px] sm:leading-9">{shown}</p>
      {needsMore ? (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="mt-3 text-sm font-bold text-primary underline-offset-4 hover:underline"
        >
          {expanded ? "بستن" : "بیشتر …"}
        </button>
      ) : null}
    </section>
  );
}
