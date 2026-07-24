"use client";

import { useMemo } from "react";
import * as Icons from "react-iconly";
import { useCategoryTree } from "@/features/catalog/queries";
import { useCatalogParams, parseIdList, encodeIdList } from "@/components/catalog/use-catalog-params";
import { Skeleton } from "@/components/ui/skeleton";
import { cn, formatNumber } from "@/lib/utils";
import type { CategoryTreeNode } from "@/types/category";

const MAX_ROOTS = 3;

function CatIcon({ name, active }: { name?: string; active?: boolean }) {
  const Cmp = (name && (Icons as Record<string, unknown>)[name]) || Icons.Category;
  const Icon = Cmp as typeof Icons.Category;
  return <Icon set="bold" primaryColor={active ? "#FFFFFF" : "#5E5F5E"} />;
}

/**
 * Top-of-catalog grandfather category carousel.
 * Multi-select up to 3 roots (OR). Clears leaf category when roots change.
 */
export function RootCategoryCarousel() {
  const { data: tree = [], isLoading } = useCategoryTree();
  const { raw, setParams } = useCatalogParams();
  const selected = useMemo(() => parseIdList(raw.get("roots")), [raw]);

  const toggle = (node: CategoryTreeNode) => {
    const exists = selected.includes(node.id);
    let next: number[];
    if (exists) next = selected.filter((id) => id !== node.id);
    else if (selected.length >= MAX_ROOTS) next = [...selected.slice(1), node.id];
    else next = [...selected, node.id];

    setParams({
      roots: encodeIdList(next),
      category: next.length === 1 ? next[0] : null,
    });
  };

  if (isLoading) {
    return (
      <div className="no-scrollbar flex gap-3 overflow-x-auto pb-1">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-[108px] w-[128px] shrink-0 rounded-2xl" />
        ))}
      </div>
    );
  }

  return (
    <div>
      <div className="mb-3 flex items-end justify-between gap-3">
        <div>
          <h2 className="text-sm font-bold text-foreground">دسته‌های اصلی</h2>
          <p className="text-[11px] text-steel">
            تا {formatNumber(MAX_ROOTS)} دسته را همزمان انتخاب کنید
          </p>
        </div>
        {selected.length > 0 && (
          <button
            type="button"
            className="text-xs font-bold text-primary"
            onClick={() => setParams({ roots: null, category: null })}
          >
            پاک کردن
          </button>
        )}
      </div>

      <div className="no-scrollbar flex gap-3 overflow-x-auto pb-1">
        <button
          type="button"
          onClick={() => setParams({ roots: null, category: null })}
          className={cn(
            "flex h-[108px] w-[128px] shrink-0 flex-col justify-between rounded-2xl border p-3 text-start transition-all",
            selected.length === 0
              ? "border-steel bg-steel text-white shadow-glass"
              : "border-border/50 bg-card text-foreground shadow-soft hover:border-steel/30",
          )}
        >
          <span
            className={cn(
              "grid h-10 w-10 place-items-center rounded-xl",
              selected.length === 0 ? "bg-white/15" : "bg-secondary",
            )}
          >
            <Icons.Category
              set="bold"
              primaryColor={selected.length === 0 ? "#FFFFFF" : "#5E5F5E"}
            />
          </span>
          <span className="text-xs font-bold leading-5">همه دسته‌ها</span>
        </button>

        {tree.map((node) => {
          const active = selected.includes(node.id);
          return (
            <button
              key={node.id}
              type="button"
              aria-pressed={active}
              onClick={() => toggle(node)}
              className={cn(
                "flex h-[108px] w-[128px] shrink-0 flex-col justify-between rounded-2xl border p-3 text-start transition-all",
                active
                  ? "border-primary bg-primary text-primary-foreground shadow-primary-glow"
                  : "border-border/50 bg-card shadow-soft hover:-translate-y-0.5 hover:border-steel/30 hover:shadow-glass",
              )}
            >
              <span
                className={cn(
                  "grid h-10 w-10 place-items-center rounded-xl",
                  active ? "bg-white/15" : "bg-secondary",
                )}
              >
                <CatIcon name={node.icon} active={active} />
              </span>
              <span>
                <span className="line-clamp-2 text-xs font-bold leading-5">{node.name}</span>
                <span
                  className={cn(
                    "mt-0.5 block text-[10px]",
                    active ? "text-white/80" : "text-steel",
                  )}
                >
                  {formatNumber(node.product_count ?? 0)}
                </span>
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
