"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, Category, CloseSquare, Search } from "react-iconly";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useCategoryTree } from "@/features/catalog/queries";
import { buildNavGroups, categoryHref, filterNonEmptyTree } from "@/config/nav-groups";
import { useFocusTrap } from "@/lib/use-focus-trap";
import { useMotionSafe } from "@/lib/use-motion-safe";
import { cn, formatNumber } from "@/lib/utils";
import type { CategoryTreeNode } from "@/types/category";

interface MobileCategoryMenuProps {
  open: boolean;
  onClose: () => void;
}

export function MobileCategoryMenu({ open, onClose }: MobileCategoryMenuProps) {
  const { data: tree = [], isLoading } = useCategoryTree();
  const groups = useMemo(() => buildNavGroups(tree), [tree]);
  const motionSafe = useMotionSafe();
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const panelRef = useRef<HTMLDivElement>(null);
  const handleEscape = useCallback(() => onClose(), [onClose]);

  useFocusTrap(panelRef, open, handleEscape);

  useEffect(() => {
    if (!open) return;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  useEffect(() => {
    if (open && groups.length && expandedId == null) {
      setExpandedId(groups[0]?.id ?? null);
    }
    if (!open) {
      setQuery("");
    }
  }, [open, groups, expandedId]);

  const visibleGroups = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return groups;
    return groups
      .map((g) => ({
        ...g,
        roots: g.roots
          .map((r) => filterByQuery(r, q))
          .filter((r): r is CategoryTreeNode => Boolean(r)),
      }))
      .filter((g) => g.roots.length > 0);
  }, [groups, query]);

  const panel = (
    <div
      ref={panelRef}
      role="dialog"
      aria-modal="true"
      aria-label="دسته‌بندی محصولات"
      className="flex h-full flex-col bg-background"
    >
      <div className="sticky top-0 z-10 border-b border-border/60 bg-background/95 px-4 pb-4 pt-[max(1rem,env(safe-area-inset-top))] backdrop-blur-md">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-accent text-primary">
              <Category set="bold" size="small" />
            </span>
            <div>
              <p className="text-base font-bold text-foreground">دسته‌بندی محصولات</p>
              <p className="text-xs text-muted-foreground">گروه‌بندی فروشگاهی</p>
            </div>
          </div>
          <button
            type="button"
            aria-label="بستن"
            onClick={onClose}
            className="touch-target rounded-xl bg-secondary text-foreground"
          >
            <CloseSquare set="bold" size="small" />
          </button>
        </div>

        <div className="relative mb-3">
          <span className="pointer-events-none absolute start-3 top-1/2 -translate-y-1/2 text-muted-foreground">
            <Search size="small" set="light" />
          </span>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="جستجوی دسته…"
            aria-label="جستجوی دسته‌بندی"
            className="h-11 w-full rounded-xl bg-input ps-9 pe-3 text-base outline-none focus:ring-2 focus:ring-ring/40"
          />
        </div>

        <Link href="/catalog" onClick={onClose} className="block">
          <Button size="lg" className="w-full gap-2 shadow-primary-glow">
            مشاهده همه محصولات
            <ArrowLeft set="bold" size="small" />
          </Button>
        </Link>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 pb-[calc(5rem+env(safe-area-inset-bottom))]">
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-14 w-full rounded-2xl" />
            ))}
          </div>
        ) : visibleGroups.length === 0 ? (
          <p className="px-2 py-6 text-center text-sm text-muted-foreground">دسته‌ای یافت نشد.</p>
        ) : (
          <ul className="space-y-2">
            {visibleGroups.map((group) => (
              <li
                key={group.id}
                className={cn(
                  "overflow-hidden rounded-2xl border border-border/70 bg-card shadow-soft",
                  group.highlight && "ring-1 ring-primary/15",
                )}
              >
                <button
                  type="button"
                  onClick={() =>
                    setExpandedId((id) => (id === group.id ? null : group.id))
                  }
                  className="flex w-full items-center justify-between px-4 py-4 text-start"
                >
                  <span className="flex flex-col gap-0.5">
                    <span
                      className={cn(
                        "text-sm font-bold",
                        group.highlight ? "text-primary" : "text-foreground",
                      )}
                    >
                      {group.label}
                    </span>
                    <span className="text-[11px] text-muted-foreground">
                      {formatNumber(group.product_count)} محصول
                    </span>
                  </span>
                  <span
                    className={cn(
                      "text-muted-foreground transition-transform",
                      expandedId === group.id && "rotate-180",
                    )}
                  >
                    ▾
                  </span>
                </button>

                {expandedId === group.id && (
                  <div className="border-t border-border/60 px-3 pb-3 pt-1">
                    {group.roots.map((root) => (
                      <MobileRoot key={root.id} root={root} onNavigate={onClose} />
                    ))}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.button
            type="button"
            aria-label="بستن منو"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: motionSafe ? 0.2 : 0.12 }}
            className="fixed inset-0 z-[60] bg-black/45 lg:hidden"
            onClick={onClose}
          />
          <motion.div
            initial={motionSafe ? { y: "100%" } : { opacity: 0 }}
            animate={motionSafe ? { y: 0 } : { opacity: 1 }}
            exit={motionSafe ? { y: "100%" } : { opacity: 0 }}
            transition={
              motionSafe
                ? { type: "spring", damping: 28, stiffness: 320 }
                : { duration: 0.15 }
            }
            className="fixed inset-x-0 bottom-0 top-0 z-[61] lg:hidden"
          >
            {panel}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

function MobileRoot({
  root,
  onNavigate,
}: {
  root: CategoryTreeNode;
  onNavigate: () => void;
}) {
  const mids = filterNonEmptyTree(root.subcategories ?? []);
  return (
    <div className="mt-2 rounded-xl bg-secondary/60 p-2">
      <Link
        href={categoryHref(root)}
        onClick={onNavigate}
        className="flex min-h-11 items-center px-1 text-sm font-bold text-foreground"
      >
        {root.name}
      </Link>
      {mids.map((mid) => (
        <div key={mid.id} className="mt-1">
          <Link
            href={categoryHref(mid)}
            onClick={onNavigate}
            className="flex min-h-11 items-center px-1 text-sm font-semibold text-foreground/90"
          >
            {mid.name}
          </Link>
          {(mid.subcategories?.length ?? 0) > 0 && (
            <ul className="space-y-0.5 ps-1">
              {mid.subcategories.map((leaf) => (
                <li key={leaf.id}>
                  <Link
                    href={categoryHref(leaf)}
                    onClick={onNavigate}
                    className="flex min-h-11 items-center px-1 text-sm text-muted-foreground hover:text-primary"
                  >
                    {leaf.name}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  );
}

function filterByQuery(node: CategoryTreeNode, q: string): CategoryTreeNode | null {
  const self = node.name.toLowerCase().includes(q);
  const kids = (node.subcategories ?? [])
    .map((c) => filterByQuery(c, q))
    .filter((c): c is CategoryTreeNode => Boolean(c));
  if (!self && kids.length === 0) return null;
  return { ...node, subcategories: kids.length ? kids : filterNonEmptyTree(node.subcategories ?? []) };
}
