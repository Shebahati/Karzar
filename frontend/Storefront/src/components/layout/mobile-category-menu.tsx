"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, Category, CloseSquare } from "react-iconly";
import * as Icons from "react-iconly";
import { Skeleton } from "@/components/ui/skeleton";
import { useCategoryTree } from "@/features/catalog/queries";
import { categoryHref } from "@/config/nav-groups";
import { useFocusTrap } from "@/lib/use-focus-trap";
import { useMotionSafe } from "@/lib/use-motion-safe";
import { cn, formatNumber } from "@/lib/utils";
import type { CategoryTreeNode } from "@/types/category";

interface MobileCategoryMenuProps {
  open: boolean;
  onClose: () => void;
}

function CatIcon({ name }: { name?: string }) {
  const Cmp = (name && (Icons as Record<string, unknown>)[name]) || Icons.Category;
  const Icon = Cmp as typeof Icons.Category;
  return <Icon set="bold" primaryColor="#5E5F5E" />;
}

/**
 * Mobile category sheet: root cards first → layer 2/3 drill-down.
 * Leaves bottom nav visible (padding-bottom).
 */
export function MobileCategoryMenu({ open, onClose }: MobileCategoryMenuProps) {
  const { data: tree = [], isLoading } = useCategoryTree();
  const motionSafe = useMotionSafe();
  const [stack, setStack] = useState<CategoryTreeNode[]>([]);
  const panelRef = useRef<HTMLDivElement>(null);
  const handleEscape = useCallback(() => onClose(), [onClose]);

  useFocusTrap(panelRef, open, handleEscape);

  useEffect(() => {
    if (!open) {
      setStack([]);
      return;
    }
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  const current = stack[stack.length - 1] ?? null;
  const children = useMemo(
    () => (current ? current.subcategories ?? [] : tree),
    [current, tree],
  );

  const title = current?.name ?? "دسته‌بندی محصولات";
  const browseHref = current ? categoryHref(current) : "/catalog";

  const panel = (
    <div
      ref={panelRef}
      role="dialog"
      aria-modal="true"
      aria-label="دسته‌بندی محصولات"
      className="flex h-full flex-col bg-background/95 backdrop-blur-xl"
    >
      <div className="sticky top-0 z-10 border-b border-border/50 bg-white/80 px-4 pb-3 pt-[max(0.75rem,env(safe-area-inset-top))] backdrop-blur-md">
        <div className="flex items-center gap-2">
          {stack.length > 0 ? (
            <button
              type="button"
              aria-label="بازگشت"
              onClick={() => setStack((s) => s.slice(0, -1))}
              className="touch-target rounded-xl bg-secondary text-steel"
            >
              <ArrowRight set="bold" size="small" />
            </button>
          ) : (
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-secondary text-steel">
              <Category set="bold" size="small" />
            </span>
          )}
          <div className="min-w-0 flex-1">
            <p className="truncate text-base font-bold text-foreground">{title}</p>
            <p className="text-xs text-steel">
              {stack.length === 0 ? "انتخاب دستهٔ اصلی" : "زیرمجموعه‌ها"}
            </p>
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

        <Link
          href={browseHref}
          onClick={onClose}
          className="mt-3 flex h-11 items-center justify-center rounded-xl bg-steel text-sm font-bold text-white"
        >
          نمایش همه محصولات{current ? ` «${current.name}»` : ""}
        </Link>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 pb-[calc(5.5rem+env(safe-area-inset-bottom))]">
        {isLoading ? (
          <div className="grid grid-cols-2 gap-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-28 rounded-2xl" />
            ))}
          </div>
        ) : children.length === 0 ? (
          <div className="rounded-2xl bg-secondary p-6 text-center text-sm text-steel">
            زیرمجموعه‌ای نیست.
            <Link
              href={browseHref}
              onClick={onClose}
              className="mt-3 block font-bold text-primary"
            >
              مشاهده محصولات
            </Link>
          </div>
        ) : (
          <div className={cn("grid gap-3", stack.length === 0 ? "grid-cols-2" : "grid-cols-1")}>
            {children.map((node) => {
              const hasKids = (node.subcategories?.length ?? 0) > 0;
              if (stack.length === 0) {
                return (
                  <button
                    key={node.id}
                    type="button"
                    onClick={() => {
                      if (hasKids) setStack([node]);
                    }}
                    className="flex h-[124px] flex-col justify-between rounded-2xl border border-border/50 bg-card p-4 text-start shadow-soft active:scale-[0.98]"
                  >
                    {hasKids ? (
                      <>
                        <span className="grid h-11 w-11 place-items-center rounded-xl bg-secondary">
                          <CatIcon name={node.icon} />
                        </span>
                        <span>
                          <span className="line-clamp-2 text-sm font-bold text-foreground">
                            {node.name}
                          </span>
                          <span className="mt-0.5 block text-[11px] text-steel">
                            {formatNumber(node.product_count ?? 0)} محصول
                          </span>
                        </span>
                      </>
                    ) : (
                      <Link href={categoryHref(node)} onClick={onClose} className="flex h-full flex-col justify-between">
                        <span className="grid h-11 w-11 place-items-center rounded-xl bg-secondary">
                          <CatIcon name={node.icon} />
                        </span>
                        <span>
                          <span className="line-clamp-2 text-sm font-bold text-foreground">
                            {node.name}
                          </span>
                          <span className="mt-0.5 block text-[11px] text-steel">
                            {formatNumber(node.product_count ?? 0)} محصول
                          </span>
                        </span>
                      </Link>
                    )}
                  </button>
                );
              }

              return (
                <div
                  key={node.id}
                  className="flex items-center gap-2 rounded-2xl border border-border/40 bg-card p-3 shadow-soft"
                >
                  {hasKids ? (
                    <button
                      type="button"
                      className="min-w-0 flex-1 text-start"
                      onClick={() => setStack((s) => [...s, node])}
                    >
                      <span className="block text-sm font-bold text-foreground">{node.name}</span>
                      <span className="text-[11px] text-steel">
                        {formatNumber(node.subcategories.length)} زیرمجموعه
                      </span>
                    </button>
                  ) : (
                    <Link
                      href={categoryHref(node)}
                      onClick={onClose}
                      className="min-w-0 flex-1"
                    >
                      <span className="block text-sm font-bold text-foreground">{node.name}</span>
                      <span className="text-[11px] text-steel">
                        {formatNumber(node.product_count ?? 0)} محصول
                      </span>
                    </Link>
                  )}
                  {hasKids && (
                    <button
                      type="button"
                      onClick={() => setStack((s) => [...s, node])}
                      className="touch-target rounded-xl bg-secondary text-steel"
                      aria-label="باز کردن"
                    >
                      <Icons.ArrowLeft set="light" size="small" />
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[60] lg:hidden"
          initial={motionSafe ? { opacity: 0 } : false}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <button
            type="button"
            aria-label="بستن پس‌زمینه"
            className="absolute inset-0 bg-steel/40 backdrop-blur-sm"
            onClick={onClose}
          />
          <motion.div
            className="absolute inset-x-0 bottom-0 top-0 overflow-hidden bg-background"
            initial={motionSafe ? { y: "8%" } : false}
            animate={{ y: 0 }}
            exit={{ y: "8%" }}
            transition={{ type: "spring", stiffness: 320, damping: 32 }}
          >
            {panel}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
