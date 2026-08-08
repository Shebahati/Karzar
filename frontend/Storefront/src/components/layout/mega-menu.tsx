"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, Search } from "react-iconly";
import { useCategoryTree } from "@/features/catalog/queries";
import { Skeleton } from "@/components/ui/skeleton";
import { categoryHref, filterNonEmptyTree, orderedTaxonomyRoots } from "@/config/nav-groups";
import { cn, formatNumber } from "@/lib/utils";
import type { CategoryTreeNode } from "@/types/category";

interface MegaMenuProps {
  open: boolean;
  onNavigate: () => void;
  onClose: () => void;
}

/**
 * Desktop mega menu — L1 categories from live DB tree only (no separate nav-groups).
 */
export function MegaMenu({ open, onNavigate, onClose }: MegaMenuProps) {
  const { data: tree = [], isLoading } = useCategoryTree();
  const roots = useMemo(
    () => filterNonEmptyTree(orderedTaxonomyRoots(tree)),
    [tree],
  );
  const [activeRootId, setActiveRootId] = useState<number | null>(null);
  const [query, setQuery] = useState("");
  const searchId = useId();
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (roots.length && activeRootId == null) {
      setActiveRootId(roots[0].id);
    }
  }, [roots, activeRootId]);

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
    const search = document.getElementById(searchId);
    search?.focus();
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose, searchId]);

  const activeRoot = roots.find((r) => r.id === activeRootId) ?? roots[0] ?? null;

  const filteredRoot = useMemo(() => {
    if (!activeRoot) return null;
    const q = query.trim().toLowerCase();
    if (!q) return activeRoot;
    return filterTreeByQuery(activeRoot, q);
  }, [activeRoot, query]);

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
            {/* Solid panel — independent of header glass/scrolled state.
                Nested backdrop-blur over a scrolled header's own blur often
                fails to composite, leaving the panel too transparent. */}
            <div
              className={cn(
                "max-h-[min(36rem,calc(100dvh-6.5rem))] overflow-hidden rounded-2xl",
                "border border-steel/10 bg-white shadow-elevated",
              )}
            >
              {isLoading ? (
                <div className="flex min-h-72">
                  <div className="w-64 space-y-2 border-e border-steel/15 p-4">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <Skeleton key={i} className="h-10 w-full rounded-xl" />
                    ))}
                  </div>
                  <div className="flex-1 space-y-3 p-6">
                    <Skeleton className="h-6 w-40" />
                    <Skeleton className="h-4 w-full" />
                  </div>
                </div>
              ) : roots.length === 0 ? (
                <p className="p-8 text-sm text-[#5E5F5E]">دسته‌بندی‌ای یافت نشد.</p>
              ) : (
                <div className="flex max-h-[min(36rem,calc(100dvh-6.5rem))] min-h-[320px]">
                  <aside className="w-64 shrink-0 overflow-y-auto overscroll-contain border-e border-steel/10 bg-[#F7F7F7] py-2">
                    {roots.map((root) => {
                      const active = activeRoot?.id === root.id;
                      return (
                        <button
                          key={root.id}
                          type="button"
                          onMouseEnter={() => setActiveRootId(root.id)}
                          onFocus={() => setActiveRootId(root.id)}
                          className={cn(
                            "flex w-full items-center justify-between gap-2 px-4 py-3 text-start text-sm transition-colors",
                            active
                              ? "bg-white font-bold text-[#1f1f1f] shadow-[inset_-3px_0_0_0_#D02327]"
                              : "font-semibold text-[#3a3a3a] hover:bg-white/80 hover:text-[#D02327]",
                          )}
                        >
                          <span className="truncate">{root.name}</span>
                          <ArrowLeft size="small" set="light" primaryColor="currentColor" />
                        </button>
                      );
                    })}
                  </aside>

                  <div className="flex min-h-0 min-w-0 flex-1 flex-col bg-white">
                    {activeRoot && (
                      <div className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b border-steel/10 px-6 py-3">
                        <div>
                          <p className="text-sm font-bold text-[#1a1a1a]">{activeRoot.name}</p>
                          <p className="text-[11px] font-medium text-[#5E5F5E]">
                            {formatNumber(activeRoot.product_count ?? 0)} محصول
                          </p>
                        </div>
                        <div className="relative min-w-[200px] max-w-xs flex-1">
                          <span className="pointer-events-none absolute start-3 top-1/2 -translate-y-1/2 text-[#5E5F5E]">
                            <Search size="small" set="light" primaryColor="currentColor" />
                          </span>
                          <input
                            id={searchId}
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            placeholder="جستجو در این دسته…"
                            aria-label="جستجو در منوی دسته‌بندی"
                            className="h-10 w-full rounded-xl border border-steel/15 bg-[#F7F7F7] ps-9 pe-3 text-base text-[#2a2a2a] outline-none placeholder:text-[#8a8a8a] focus:bg-white focus:ring-2 focus:ring-steel/25"
                          />
                        </div>
                      </div>
                    )}
                    <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain p-6">
                      {!filteredRoot ? (
                        <p className="text-sm text-[#5E5F5E]">نتیجه‌ای یافت نشد.</p>
                      ) : (
                        <MegaMenuRoot root={filteredRoot} onNavigate={onNavigate} />
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
          className="text-sm font-bold text-[#1a1a1a] transition-colors hover:text-[#D02327]"
        >
          {root.name}
        </Link>
        <Link
          href={categoryHref(root)}
          onClick={onNavigate}
          className="text-xs font-bold text-[#D02327] hover:underline"
        >
          مشاهده همه
        </Link>
      </div>
      {mids.length === 0 ? (
        <Link
          href={categoryHref(root)}
          onClick={onNavigate}
          className="inline-flex text-sm font-medium text-[#4a4a4a] transition-colors hover:text-[#D02327]"
        >
          مشاهده محصولات {root.name}
        </Link>
      ) : (
        <div className="grid grid-cols-2 gap-x-8 gap-y-6 xl:grid-cols-3">
          {mids.map((mid) => {
            const kids = mid.subcategories ?? [];
            const isBranch = kids.length > 0;
            return (
              <div key={mid.id} className="min-w-0">
                <Link
                  href={categoryHref(mid)}
                  onClick={onNavigate}
                  className={cn(
                    "block text-sm transition-colors hover:text-[#D02327]",
                    isBranch
                      ? "font-bold text-[#2a2a2a]"
                      : "font-semibold text-[#3d3d3d]",
                  )}
                >
                  {mid.name}
                </Link>
                {isBranch ? (
                  <ul className="mt-2.5 space-y-1.5">
                    {kids.map((leaf) => (
                      <li key={leaf.id}>
                        <Link
                          href={categoryHref(leaf)}
                          onClick={onNavigate}
                          className="block truncate text-sm font-medium text-[#5E5F5E] transition-colors hover:text-[#D02327]"
                        >
                          {leaf.name}
                        </Link>
                      </li>
                    ))}
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
  return {
    ...node,
    subcategories: kids.length ? kids : filterNonEmptyTree(node.subcategories ?? []),
  };
}
