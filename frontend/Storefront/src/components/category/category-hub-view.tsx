"use client";

import Link from "next/link";
import { ChevronLeft } from "react-iconly";
import { Container } from "@/components/ui/container";
import { CatalogView } from "@/components/catalog/catalog-view";
import { useFlatCategories } from "@/features/catalog/queries";
import { categoryHref } from "@/config/nav-groups";
import { formatNumber } from "@/lib/utils";
import type { CategoryFlat } from "@/types/category";

export function CategoryHubView({ category }: { category: CategoryFlat }) {
  const { data: all = [] } = useFlatCategories();
  const byId = new Map(all.map((c) => [c.id, c]));
  const pathIds = [...(category.ancestor_ids ?? []), category.id];
  const crumbs = pathIds
    .map((id) => byId.get(id))
    .filter((c): c is CategoryFlat => Boolean(c));

  return (
    <>
      <Container className="pt-6 pb-2">
        <nav
          aria-label="breadcrumb"
          className="mb-4 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground"
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

        <header className="mb-6 max-w-3xl">
          <h1 className="text-2xl font-bold text-foreground sm:text-3xl">{category.name}</h1>
          {category.meta_description || category.breadcrumb?.length ? (
            <p className="mt-2 text-sm leading-7 text-muted-foreground">
              {category.meta_description ||
                `محصولات دسته «${category.breadcrumb?.join(" › ") ?? category.name}» در فروشگاه کارزار.`}
            </p>
          ) : null}
          {typeof category.product_count === "number" ? (
            <p className="mt-2 text-xs font-bold text-primary">
              {formatNumber(category.product_count)} محصول در این شاخه
            </p>
          ) : null}
        </header>
      </Container>

      <CatalogView lockedCategoryId={category.id} />
    </>
  );
}
