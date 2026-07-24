"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, Search } from "react-iconly";
import { useCategoryTree } from "@/features/catalog/queries";
import { Skeleton } from "@/components/ui/skeleton";
import { buildNavGroups, categoryHref, filterNonEmptyTree } from "@/config/nav-groups";
import { cn, formatNumber } from "@/lib/utils";
import type { CategoryTreeNode } from "@/types/category";

interface MegaMenuProps {
  open: boolean;
  onNavigate: () => void;
  onClose: () => void;
}

/**
 * Desktop mega menu: 5 merchandising groups, search, hide empty categories.
 */
export function MegaMenu({ open, onNavigate, onClose }: MegaMenuProps) {
  const { data: tree = [], isLoading } = useCategoryTree();
  const groups = useMemo(() => buildNavGroups(tree), [tree]);
  const [activeGroupId, setActiveGroupId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const panelId = useId();
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (groups.length && activeGroupId == null) {
      setActiveGroupId(groups[0].id);
    }
  }, [groups, activeGroupId]);

  useEffect(() => {
    if (!open) {
      setQuery("");
      return;
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const activeGroup = groups.find((g) => g.id === activeGroupId) ?? groups[0] ?? null;

  const filteredRoots = useMemo(() => {
    if (!activeGroup) return [];
    const q = query.trim().toLowerCase();
    if (!q) return activeGroup.roots.map((r) => filterNonEmptyTree([r])[0]).filter(Boolean);
    return activeGroup.roots
      .map((root) => filterTreeByQuery(root, q))
      .filter((r): r is CategoryTreeNode => Boolean(r));
  }, [activeGroup, query]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          id={panelId}
          ref={panelRef}
          role="region"
          aria-label="منوی دسته‌بندی محصولات"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15, ease: "easeOut" }}
          className="absolute inset-x-0 top-full z-40 hidden lg:block"
        >
          <div className="h-2 w-full" aria-hidden />
          <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
            className="mx-auto max-w-[1320px] px-5 sm:px-6 lg:px-8"
          >
            <div className="overflow-hidden rounded-2xl border border-border/70 bg-card shadow-elevated">
              {isLoading ? (
                <div className="flex min-h-72">
                  <div className="w-64 space-y-2 border-e border-border/60 p-4">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <Skeleton key={i} className="h-10 w-full rounded-xl" />
                    ))}
                  </div>
                  <div className="flex-1 space-y-3 p-6">
                    <Skeleton className="h-6 w-40" />
                    <Skeleton className="h-4 w-full" />
                  </div>
                </div>
              ) : groups.length === 0 ? (
                <p className="p-8 text-sm text-muted-foreground">دسته‌بندی‌ای یافت نشد.</p>
              ) : (
                <div className="flex min-h-[320px] max-h-[min(72vh,560px)]">
                  <aside className="w-64 shrink-0 overflow-y-auto border-e border-border/60 bg-muted/30 py-2">
                    {groups.map((group) => {
                      const active = activeGroup?.id === group.id;
                      return (
                        <button
                          key={group.id}
                          type="button"
                          onMouseEnter={() => setActiveGroupId(group.id)}
                          onFocus={() => setActiveGroupId(group.id)}
                          className={cn(
                            "flex w-full items-center justify-between gap-2 px-4 py-3 text-start text-sm font-bold transition-colors",
                            active ? "bg-card text-primary" : "text-foreground hover:text-primary",
                            group.highlight && !active && "text-primary/90",
                          )}
                        >
                          <span className="truncate">{group.label}</span>
                          {group.highlight ? (
                            <span className="shrink-0 rounded-md bg-accent px-1.5 py-0.5 text-[10px] font-bold text-primary">
                              ویژه
                            </span>
                          ) : (
                            <ArrowLeft size="small" set="light" />
                          )}
                        </button>
                      );
                    })}
                  </aside>

                  <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
                    {activeGroup && (
                      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 px-6 py-3">
                        <div>
                          <p className="text-sm font-bold text-foreground">{activeGroup.label}</p>
                          <p className="text-[11px] text-muted-foreground">
                            {formatNumber(activeGroup.product_count)} محصول
                          </p>
                        </div>
                        <div className="relative min-w-[200px] flex-1 max-w-xs">
                          <span className="pointer-events-none absolute start-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                            <Search size="small" set="light" />
                          </span>
                          <input
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            placeholder="جستجو در این گروه…"
                            aria-label="جستجو در منوی دسته‌بندی"
                            className="h-10 w-full rounded-xl bg-input ps-9 pe-3 text-sm outline-none focus:ring-2 focus:ring-ring/40"
                          />
                        </div>
                      </div>
                    )}
                    <div className="flex-1 overflow-y-auto p-6">
                      {filteredRoots.length === 0 ? (
                        <p className="text-sm text-muted-foreground">نتیجه‌ای یافت نشد.</p>
                      ) : (
                        <div className="space-y-8">
                          {filteredRoots.map((root) => (
                            <MegaMenuRoot key={root.id} root={root} onNavigate={onNavigate} />
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function MegaMenuRoot({
  root,
  onNavigate,
}: {
  root: CategoryTreeNode;
  onNavigate: () => void;
}) {
  const mids = filterNonEmptyTree(root.subcategories ?? []);
  return (
    <div>
      <div className="mb-3 flex items-center justify-between gap-3">
        <Link
          href={categoryHref(root)}
          onClick={onNavigate}
          className="text-sm font-bold text-foreground hover:text-primary"
        >
          {root.name}
        </Link>
        <Link
          href={categoryHref(root)}
          onClick={onNavigate}
          className="text-xs font-bold text-primary hover:underline"
        >
          مشاهده همه
        </Link>
      </div>
      {mids.length === 0 ? (
        <Link
          href={categoryHref(root)}
          onClick={onNavigate}
          className="inline-flex text-sm font-bold text-primary hover:underline"
        >
          مشاهده محصولات {root.name}
        </Link>
      ) : (
        <div className="grid grid-cols-2 gap-x-8 gap-y-6 xl:grid-cols-3">
          {mids.map((mid) => (
            <div key={mid.id} className="min-w-0">
              <Link
                href={categoryHref(mid)}
                onClick={onNavigate}
                className="block text-sm font-bold text-foreground transition-colors hover:text-primary"
              >
                {mid.name}
              </Link>
              {(mid.subcategories?.length ?? 0) > 0 ? (
                <ul className="mt-2.5 space-y-1.5">
                  {mid.subcategories.map((leaf) => (
                    <li key={leaf.id}>
                      <Link
                        href={categoryHref(leaf)}
                        onClick={onNavigate}
                        className="block truncate text-sm text-muted-foreground transition-colors hover:text-primary"
                      >
                        {leaf.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function filterTreeByQuery(node: CategoryTreeNode, q: string): CategoryTreeNode | null {
  const selfMatch = node.name.toLowerCase().includes(q);
  const kids = (node.subcategories ?? [])
    .map((c) => filterTreeByQuery(c, q))
    .filter((c): c is CategoryTreeNode => Boolean(c));
  if (!selfMatch && kids.length === 0) return null;
  if ((node.product_count ?? 0) === 0 && kids.length === 0 && !selfMatch) return null;
  return { ...node, subcategories: kids.length ? kids : filterNonEmptyTree(node.subcategories ?? []) };
}
