"use client";

import Link from "next/link";
import { useMemo } from "react";
import * as Icons from "react-iconly";
import { useCategoryTree } from "@/features/catalog/queries";
import { Skeleton } from "@/components/ui/skeleton";
import { AutoCarousel } from "@/components/ui/auto-carousel";
import { categoryHref } from "@/config/nav-groups";
import { cn, formatNumber } from "@/lib/utils";
import type { CategoryTreeNode } from "@/types/category";

function CategoryIcon({ name }: { name?: string }) {
  const Cmp = (name && (Icons as Record<string, unknown>)[name]) || Icons.Category;
  const Icon = Cmp as typeof Icons.Category;
  return <Icon size="large" set="bold" primaryColor="#5E5F5E" />;
}

function CategoryCard({ node }: { node: CategoryTreeNode }) {
  return (
    <Link
      href={categoryHref(node)}
      className={cn(
        "group relative flex h-[168px] w-[148px] flex-col justify-between overflow-hidden rounded-2xl border border-border/50 bg-card p-4 shadow-soft transition-all duration-300 sm:h-[180px] sm:w-[168px]",
        "hover:-translate-y-1 hover:border-steel/30 hover:shadow-glass",
      )}
    >
      <div
        className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        style={{
          background:
            "linear-gradient(145deg, rgba(94,95,94,0.06) 0%, rgba(194,32,38,0.08) 100%)",
        }}
      />
      <span className="relative grid h-12 w-12 place-items-center rounded-xl bg-secondary text-steel transition-colors group-hover:bg-accent group-hover:text-primary">
        <CategoryIcon name={node.icon} />
      </span>
      <div className="relative">
        <span className="line-clamp-2 text-sm font-bold leading-6 text-foreground">
          {node.name}
        </span>
        <span className="mt-1 block text-[11px] text-steel">
          {formatNumber(node.product_count ?? 0)} محصول
        </span>
      </div>
    </Link>
  );
}

/** Root (grandfather) category carousel for the home page. */
export function CategoryGrid() {
  const { data, isLoading } = useCategoryTree();
  const roots = useMemo(() => data ?? [], [data]);

  if (isLoading) {
    return (
      <div className="flex gap-3 overflow-hidden">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-[168px] w-[148px] shrink-0 rounded-2xl" />
        ))}
      </div>
    );
  }

  if (!roots.length) return null;

  return (
    <AutoCarousel autoPlay intervalMs={2800} itemClassName="w-auto">
      {[...roots, ...roots].map((node, i) => (
        <CategoryCard key={`${node.id}-${i}`} node={node} />
      ))}
    </AutoCarousel>
  );
}
