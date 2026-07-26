"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, Search } from "react-iconly";
import { useCategoryTree, useNavGroupDefs } from "@/features/catalog/queries";
import { Skeleton } from "@/components/ui/skeleton";
import { buildNavGroups, categoryHref, filterNonEmptyTree, NAV_GROUPS } from "@/config/nav-groups";
import {
  prepareMegamenuRoots,
  resolveMegamenuBold,
} from "@/lib/megamenu-display";
import { cn, formatNumber } from "@/lib/utils";
import type { CategoryTreeNode } from "@/types/category";

interface MegaMenuProps {
  open: boolean;
  onNavigate: () => void;
  onClose: () => void;
}

/**
 * Desktop mega menu: merchandising groups from API (hardcoded fallback), search, hide empty.
 */
export function MegaMenu({ open, onNavigate, onClose }: MegaMenuProps) {
  const { data: tree = [], isLoading } = useCategoryTree();
  const { data: navDefs = NAV_GROUPS } = useNavGroupDefs();
  const groups = useMemo(() => buildNavGroups(tree, navDefs), [tree, navDefs]);
  const [activeGroupId, setActiveGroupId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const searchId = useId();
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
    const panel = panelRef.current;
    const focusables = () =>
      panel
        ? Array.from(
            panel.querySelectorAll<HTMLElement>(
              'button:not([disabled]), a[href], input:not([disabled]), [tabindex]:not([tabindex="-1"])',
            ),
          )
        : [];
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        document.getElementById("karzar-mega-menu-trigger")?.focus();
        return;
      }
      if (e.key !== "Tab") return;
      const items = focusables();
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    // Focus search when panel opens for keyboard users.
    const search = document.getElementById(searchId);
    search?.focus();
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose, searchId]);

  const activeGroup = groups.find((g) => g.id === activeGroupId) ?? groups[0] ?? null;

  const filteredRoots = useMemo(() => {
    if (!activeGroup) return [];
    const q = query.trim().toLowerCase();
    const base = prepareMegamenuRoots(
      activeGroup.roots.map((r) => filterNonEmptyTree([r])[0]).filter(Boolean) as CategoryTreeNode[],
    );
    if (!q) return base;
    return base
      .map((root) => filterTreeByQuery(root, q))
      .filter((r): r is CategoryTreeNode => Boolean(r));
  }, [activeGroup, query]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          id="karzar-mega-menu"
          ref={panelRef}
          role="dialog"
          aria-modal="true"
          aria-labelledby="karzar-mega-menu-trigger"
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
            <div className="max-h-[min(36rem,calc(100dvh-6.5rem))] overflow-hidden rounded-2xl border border-white/50 bg-white/75 shadow-elevated backdrop-blur-2xl supports-[backdrop-filter]:bg-white/65">
              {isLoading ? (
                <div className="flex min-h-72">
                  <div className="w-64 space-y-2 border-e border-border/40 p-4">
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
                <div className="flex max-h-[min(36rem,calc(100dvh-6.5rem))] min-h-[320px]">
                  <aside className="w-64 shrink-0 overflow-y-auto overscroll-contain border-e border-border/40 bg-steel/[0.04] py-2">
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
                            active ? "bg-white/80 text-primary" : "text-foreground hover:text-primary",
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

                  <div className="flex min-h-0 min-w-0 flex-1 flex-col">
                    {activeGroup && (
                      <div className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-border/40 px-6 py-3">
                        <div>
                          <p className="text-sm font-bold text-foreground">{activeGroup.label}</p>
                          <p className="text-[11px] text-steel">
                            {formatNumber(activeGroup.product_count)} محصول
                          </p>
                        </div>
                        <div className="relative min-w-[200px] max-w-xs flex-1">
                          <span className="pointer-events-none absolute start-3 top-1/2 -translate-y-1/2 text-steel">
                            <Search size="small" set="light" />
                          </span>
                          <input
                            id={searchId}
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            placeholder="جستجو در این گروه…"
                            aria-label="جستجو در منوی دسته‌بندی"
                            className="h-10 w-full rounded-xl bg-white/70 ps-9 pe-3 text-sm outline-none backdrop-blur focus:ring-2 focus:ring-steel/20"
                          />
                        </div>
                      </div>
                    )}
                    <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain p-6">
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
  const mids = root.subcategories ?? [];
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
          className="inline-flex text-sm text-muted-foreground transition-colors hover:text-primary"
        >
          مشاهده محصولات {root.name}
        </Link>
      ) : (
        <div className="grid grid-cols-2 gap-x-8 gap-y-6 xl:grid-cols-3">
          {mids.map((mid) => {
            const kids = mid.subcategories ?? [];
            const isBranch = kids.length > 0;
            const bold = resolveMegamenuBold(mid, { isBranch });
            return (
              <div key={mid.id} className="min-w-0">
                <Link
                  href={categoryHref(mid)}
                  onClick={onNavigate}
                  className={cn(
                    "block text-sm transition-colors hover:text-primary",
                    bold ? "font-bold text-foreground" : "text-muted-foreground",
                  )}
                >
                  {mid.name}
                </Link>
                {isBranch ? (
                  <ul className="mt-2.5 space-y-1.5">
                    {kids.map((leaf) => {
                      const leafBold = resolveMegamenuBold(leaf, { isBranch: false });
                      return (
                        <li key={leaf.id}>
                          <Link
                            href={categoryHref(leaf)}
                            onClick={onNavigate}
                            className={cn(
                              "block truncate text-sm transition-colors hover:text-primary",
                              leafBold ? "font-bold text-foreground" : "text-muted-foreground",
                            )}
                          >
                            {leaf.name}
                          </Link>
                        </li>
                      );
                    })}
                  </ul>
                ) : null}
              </div>
            );
          })}
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
