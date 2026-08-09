"use client";

import { useEffect, useMemo, useState, type MouseEvent } from "react";
import { ChevronDown, ChevronLeft, CloseSquare, Search } from "react-iconly";
import {
  FilterShowMoreButton,
  useFilterShowMore,
} from "@/components/catalog/filter-show-more";
import { useCategoryTree, useFlatCategories } from "@/features/catalog/queries";
import { cn, formatNumber, toPersianDigits } from "@/lib/utils";
import type { CategoryFlat, CategoryTreeNode } from "@/types/category";

function normalizeFa(s: string): string {
  return s
    .trim()
    .toLowerCase()
    .replace(/\u200c/g, " ")
    .replace(/\s+/g, " ")
    .replace(/ي/g, "ی")
    .replace(/ك/g, "ک");
}

function collectAncestorIds(id: number, byId: Map<number, CategoryFlat>): number[] {
  const ids: number[] = [];
  let current = byId.get(id);
  while (current?.parent_id != null) {
    ids.push(current.parent_id);
    current = byId.get(current.parent_id);
  }
  return ids;
}

/** Keep API tree order; drop empty leaves (count 0, no children). */
function pruneEmptyLeaves(
  nodes: CategoryTreeNode[],
  activeId?: number | null,
): CategoryTreeNode[] {
  return nodes
    .map((node) => ({
      ...node,
      subcategories: pruneEmptyLeaves(node.subcategories ?? [], activeId),
    }))
    .filter((node) => {
      if (node.id === activeId) return true;
      const kids = node.subcategories?.length ?? 0;
      if (kids > 0) return true;
      if (node.product_count == null) return true;
      return node.product_count > 0;
    });
}

function filterTreeByQuery(
  nodes: CategoryTreeNode[],
  query: string,
): { tree: CategoryTreeNode[]; expandIds: Set<number> } {
  const q = normalizeFa(query);
  if (!q) return { tree: nodes, expandIds: new Set() };
  const expandIds = new Set<number>();
  const walk = (list: CategoryTreeNode[]): CategoryTreeNode[] => {
    const out: CategoryTreeNode[] = [];
    for (const node of list) {
      const kids = walk(node.subcategories ?? []);
      const selfMatch = normalizeFa(node.name).includes(q);
      if (selfMatch || kids.length > 0) {
        if (kids.length > 0) expandIds.add(node.id);
        out.push({ ...node, subcategories: kids });
      }
    }
    return out;
  };
  return { tree: walk(nodes), expandIds };
}

/**
 * Shop category filter backed by live GET /categories/tree.
 * Selection writes URL ?category=<id>; CatalogView maps that to API
 * GET /products/?category_id=<id> (backend expands to the full subtree).
 */
export function CategoryTreeFilter({
  activeId,
  onSelect,
  onClear,
  /** Section accordion — collapsed by default; user expands intentionally. */
  defaultOpen = false,
}: {
  activeId?: number | null;
  onSelect: (id: number) => void;
  onClear: () => void;
  defaultOpen?: boolean;
}) {
  const { data: tree = [], isLoading: treeLoading } = useCategoryTree();
  const { data: flat = [], isLoading: flatLoading } = useFlatCategories();
  const [query, setQuery] = useState("");
  const [sectionOpen, setSectionOpen] = useState(defaultOpen);

  const byId = useMemo(() => new Map(flat.map((c) => [c.id, c])), [flat]);

  const activeAncestors = useMemo(() => {
    if (activeId == null) return new Set<number>();
    return new Set([activeId, ...collectAncestorIds(activeId, byId)]);
  }, [activeId, byId]);

  const baseTree = useMemo(() => pruneEmptyLeaves(tree, activeId), [tree, activeId]);
  const { tree: visibleTree, expandIds: searchExpandIds } = useMemo(
    () => filterTreeByQuery(baseTree, query),
    [baseTree, query],
  );

  const [expanded, setExpanded] = useState<Set<number>>(() => new Set());

  useEffect(() => {
    if (activeAncestors.size === 0) return;
    setExpanded((prev) => {
      const next = new Set(prev);
      activeAncestors.forEach((id) => next.add(id));
      return next;
    });
  }, [activeAncestors]);

  useEffect(() => {
    if (!query.trim()) return;
    setExpanded((prev) => {
      const next = new Set(prev);
      searchExpandIds.forEach((id) => next.add(id));
      return next;
    });
  }, [query, searchExpandIds]);

  const selected = activeId != null ? byId.get(activeId) : undefined;
  const loading = treeLoading || flatLoading;

  // Root rows can be long; preview first 20 when browsing (search shows full matches).
  const searching = Boolean(query.trim());
  const rootShowMore = useFilterShowMore(visibleTree.length, query);
  const displayedRoots = searching
    ? visibleTree
    : visibleTree.slice(0, rootShowMore.visibleCount);
  const showRootMore = !searching && rootShowMore.canShowMore;

  const toggleExpand = (id: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleClear = (e?: MouseEvent) => {
    e?.preventDefault();
    e?.stopPropagation();
    setQuery("");
    onClear();
  };

  const handleSelect = (id: number, e?: MouseEvent) => {
    e?.preventDefault();
    e?.stopPropagation();
    if (activeId === id) {
      handleClear();
      return;
    }
    onSelect(id);
  };

  const renderNode = (node: CategoryTreeNode, depth: number) => {
    const kids = node.subcategories ?? [];
    const hasKids = kids.length > 0;
    const isOpen = expanded.has(node.id);
    const isActive = activeId === node.id;
    const isAncestor = !isActive && activeAncestors.has(node.id);
    const flatMeta = byId.get(node.id);
    const count = node.product_count ?? flatMeta?.product_count;
    const isBranch = flatMeta ? !flatMeta.is_selectable : hasKids;
    const panelId = `shop-cat-panel-${node.id}`;

    return (
      <li key={node.id} className="relative">
        <div
          className={cn(
            "group flex items-stretch gap-0.5 rounded-xl transition-colors",
            isActive && "bg-[#D02327]/[0.08]",
            isAncestor && !isActive && "bg-[#5E5F5E]/[0.04]",
          )}
          style={{ paddingInlineStart: `${depth * 0.65}rem` }}
        >
          {hasKids ? (
            <button
              type="button"
              aria-expanded={isOpen}
              aria-controls={panelId}
              aria-label={isOpen ? `بستن ${node.name}` : `باز کردن ${node.name}`}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                toggleExpand(node.id);
              }}
              className="grid h-10 w-9 shrink-0 place-items-center rounded-lg text-[#5E5F5E] transition hover:bg-white/80"
            >
              <span
                className={cn(
                  "inline-flex transition-transform duration-200 ease-out",
                  isOpen ? "-rotate-90" : "rotate-0",
                )}
                aria-hidden
              >
                <ChevronLeft size="small" set="light" primaryColor="#5E5F5E" />
              </span>
            </button>
          ) : (
            <span className="grid h-10 w-9 shrink-0 place-items-center" aria-hidden>
              <span className="h-1 w-1 rounded-full bg-[#5E5F5E]/35" />
            </span>
          )}

          <button
            type="button"
            onClick={(e) => handleSelect(node.id, e)}
            aria-pressed={isActive}
            aria-current={isActive ? "true" : undefined}
            className={cn(
              "flex min-h-10 min-w-0 flex-1 items-center gap-2 rounded-xl pe-2.5 text-start transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#D02327]/35",
              isActive
                ? "font-black text-[#D02327]"
                : depth === 0
                  ? "font-bold text-foreground hover:text-[#D02327]"
                  : "font-semibold text-foreground/85 hover:text-foreground",
            )}
          >
            <span className="min-w-0 flex-1 truncate text-[13px] leading-snug">{node.name}</span>
            {isBranch ? (
              <span className="shrink-0 rounded-md bg-[#5E5F5E]/[0.08] px-1.5 py-0.5 text-[9px] font-bold text-[#5E5F5E]/80">
                شاخه
              </span>
            ) : null}
            {count != null && count > 0 ? (
              <span
                className={cn(
                  "shrink-0 tabular-nums text-[10px] font-bold",
                  isActive ? "text-[#D02327]/75" : "text-[#5E5F5E]/55",
                )}
              >
                {formatNumber(count)}
              </span>
            ) : null}
          </button>
        </div>

        {hasKids && isOpen ? (
          <ul id={panelId} role="group" className="ms-3 border-s border-[#5E5F5E]/15 ps-1">
            {kids.map((child) => renderNode(child, depth + 1))}
          </ul>
        ) : null}
      </li>
    );
  };

  return (
    <section
      aria-labelledby="shop-category-filter-heading"
      className="overflow-hidden rounded-2xl border border-[#D02327]/15 bg-gradient-to-b from-[#D02327]/[0.06] via-card to-card shadow-[0_10px_28px_-18px_rgba(208,35,39,0.35)]"
    >
      <header className="border-b border-[#D02327]/10 bg-card/95 px-3.5 pb-3 pt-3.5">
        <div className="mb-2.5 flex items-start justify-between gap-2">
          <button
            type="button"
            aria-expanded={sectionOpen}
            aria-controls="shop-category-filter-body"
            onClick={() => setSectionOpen((v) => !v)}
            className="min-w-0 flex-1 rounded-lg text-start outline-none focus-visible:ring-2 focus-visible:ring-[#D02327]/35"
          >
            <div className="flex items-center gap-2">
              <span aria-hidden className="h-5 w-1 shrink-0 rounded-full bg-[#D02327]" />
              <span
                id="shop-category-filter-heading"
                className="text-sm font-black tracking-tight text-foreground"
              >
                دسته‌بندی
              </span>
              {activeId != null ? (
                <span className="rounded-md bg-[#D02327] px-1.5 py-0.5 text-[10px] font-bold text-white">
                  {toPersianDigits(1)}
                </span>
              ) : null}
              <span
                className={cn(
                  "ms-auto grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[#5E5F5E]/[0.08] text-[#5E5F5E] transition-transform duration-300 ease-out",
                  sectionOpen && "rotate-180",
                )}
                aria-hidden
              >
                <ChevronDown size="small" set="light" primaryColor="#5E5F5E" />
              </span>
            </div>
            {selected?.name ? (
              <p className="mt-1 ps-3 text-[11px] leading-relaxed text-[#5E5F5E]">
                {selected.name}
              </p>
            ) : null}
          </button>
          {activeId != null ? (
            <button
              type="button"
              onClick={handleClear}
              className="inline-flex min-h-9 shrink-0 items-center gap-1 rounded-lg px-2 text-[11px] font-bold text-[#D02327] hover:bg-[#D02327]/10"
            >
              <CloseSquare size={14} set="bold" primaryColor="#D02327" />
              پاک کردن
            </button>
          ) : null}
        </div>

        {sectionOpen ? (
          <div className="relative">
            <span className="pointer-events-none absolute start-3 top-1/2 -translate-y-1/2 text-[#5E5F5E]/70">
              <Search size="small" set="light" />
            </span>
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="جستجوی دسته…"
              aria-label="جستجوی دسته‌بندی"
              className="h-11 w-full rounded-xl border border-[#5E5F5E]/12 bg-white ps-9 pe-3 text-base text-foreground outline-none transition placeholder:text-[#5E5F5E]/45 focus:border-[#D02327]/35 focus:ring-2 focus:ring-[#D02327]/20"
            />
          </div>
        ) : null}
      </header>

      <div
        id="shop-category-filter-body"
        hidden={!sectionOpen}
        className="px-2.5 pb-3 pt-2"
      >
          <button
            type="button"
            onClick={handleClear}
            aria-pressed={activeId == null}
            className={cn(
              "mb-2 flex min-h-10 w-full items-center justify-between rounded-xl px-3 text-start text-[13px] font-bold transition-colors",
              activeId == null
                ? "bg-[#D02327] text-white shadow-[0_8px_18px_-10px_rgba(208,35,39,0.55)]"
                : "bg-white text-[#5E5F5E] ring-1 ring-[#5E5F5E]/10 hover:ring-[#D02327]/25",
            )}
          >
            <span>همه کالاها</span>
            {activeId == null ? (
              <span className="text-[10px] font-bold opacity-90">فعال</span>
            ) : null}
          </button>

          <div role="tree" aria-label="درخت دسته‌بندی محصولات">
            {loading ? (
              <p className="px-2 py-4 text-xs text-[#5E5F5E]">در حال بارگذاری…</p>
            ) : visibleTree.length === 0 ? (
              <p className="px-2 py-4 text-xs text-[#5E5F5E]">
                {query.trim() ? "دسته‌ای یافت نشد." : "دسته‌ای موجود نیست."}
              </p>
            ) : (
              <>
                <ul className="space-y-0.5" role="group">
                  {displayedRoots.map((node) => renderNode(node, 0))}
                </ul>
                {showRootMore ? (
                  <FilterShowMoreButton
                    remaining={rootShowMore.remaining}
                    onClick={rootShowMore.showMore}
                  />
                ) : null}
              </>
            )}
          </div>
      </div>
    </section>
  );
}
