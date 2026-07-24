"use client";

import Link from "next/link";
import { useMemo } from "react";
import * as Icons from "react-iconly";
import { useCategoryTree } from "@/features/catalog/queries";
import { Skeleton } from "@/components/ui/skeleton";
import { buildNavGroups, categoryHref } from "@/config/nav-groups";
import { cn, formatNumber } from "@/lib/utils";

function CategoryIcon({ name }: { name?: string }) {
  const Cmp = (name && (Icons as Record<string, unknown>)[name]) || Icons.Category;
  const Icon = Cmp as typeof Icons.Category;
  return <Icon size="large" set="bold" primaryColor="#C22026" />;
}

export function CategoryGrid() {
  const { data, isLoading } = useCategoryTree();
  const groups = useMemo(() => buildNavGroups(data ?? []), [data]);

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5 sm:gap-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-32 rounded-2xl sm:h-36" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5 sm:gap-4">
      {groups.map((group) => {
        const primary = group.roots[0];
        const href = primary
          ? categoryHref(primary)
          : `/catalog?search=${encodeURIComponent(group.label)}`;
        const icon = primary?.icon;
        return (
          <Link
            key={group.id}
            href={href}
            className={cn(
              "group relative overflow-hidden rounded-2xl border border-border/60 bg-card p-4 text-center shadow-soft transition-colors hover:border-primary/25 hover:bg-accent/30 sm:p-6",
              group.highlight && "border-primary/20 bg-accent/20",
            )}
          >
            <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-accent sm:h-16 sm:w-16">
              <CategoryIcon name={icon} />
            </span>
            <span
              className={cn(
                "mt-3 block text-sm font-bold",
                group.highlight ? "text-primary" : "text-foreground",
              )}
            >
              {group.label}
            </span>
            <span className="mt-1 block text-[11px] text-muted-foreground">
              {formatNumber(group.product_count)} محصول
              {group.roots.length > 1
                ? ` · ${formatNumber(group.roots.length)} ریشه`
                : ""}
            </span>
          </Link>
        );
      })}
    </div>
  );
}
