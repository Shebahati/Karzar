"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { Category, Search, Buy } from "react-iconly";
import { SafeImage } from "@/components/ui/safe-image";
import { CategoryVisualIcon } from "@/components/ui/category-visual-icon";
import { useBrands, useCategoryTree, useProducts } from "@/features/catalog/queries";
import { categoryHref } from "@/config/nav-groups";
import {
  CATEGORY_ICON_BY_SLUG,
  resolveCategoryIconUrl,
} from "@/config/category-icons";
import { FINAL_L1_CATEGORIES } from "@/config/l1-categories";
import { productPath } from "@/lib/product-url";
import { cn, formatToman, toEnglishDigits, toPersianDigits } from "@/lib/utils";
import type { CategoryTreeNode } from "@/types/category";
import type { ProductSummary } from "@/types/product";

const INITIAL_PRODUCT_COUNT = 4;
const SEARCH_PRODUCT_COUNT = 8;
const SEARCH_CATEGORY_COUNT = 6;
const SEARCH_BRAND_COUNT = 4;

function useDebounced(value: string, ms = 220) {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = window.setTimeout(() => setV(value), ms);
    return () => window.clearTimeout(t);
  }, [value, ms]);
  return v;
}

function normalize(s: string) {
  return toEnglishDigits(s)
    .trim()
    .toLowerCase()
    .replace(/ي/g, "ی")
    .replace(/ك/g, "ک")
    .replace(/\s+/g, " ");
}

function scoreProduct(p: ProductSummary, q: string): number {
  if (!q) return 0;
  const name = normalize(p.name);
  const sku = normalize(p.sku ?? "");
  const brand = normalize(p.brand?.name ?? "");
  const cat = normalize(p.category?.name ?? "");
  let score = 0;
  if (name === q) score += 100;
  if (name.startsWith(q)) score += 60;
  if (name.includes(q)) score += 40;
  if (sku.includes(q)) score += 50;
  if (brand.includes(q)) score += 25;
  if (cat.includes(q)) score += 15;
  if (p.discount_percent && p.discount_percent > 0) score += 5;
  if (p.availability) score += 3;
  return score;
}

function flattenCategoryTree(nodes: CategoryTreeNode[]): CategoryTreeNode[] {
  const out: CategoryTreeNode[] = [];
  const walk = (list: CategoryTreeNode[]) => {
    for (const n of list) {
      out.push(n);
      if (n.subcategories?.length) walk(n.subcategories);
    }
  };
  walk(nodes);
  return out;
}

type SpotlightSearchProps = {
  open: boolean;
  onClose: () => void;
  initialQuery?: string;
};

export function SpotlightSearch({ open, onClose, initialQuery = "" }: SpotlightSearchProps) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState(initialQuery);
  const [activeIndex, setActiveIndex] = useState(0);
  const debounced = useDebounced(query, 200);
  const qNorm = normalize(debounced);
  const isInitial = !qNorm;

  const productsQuery = useProducts({
    limit: qNorm ? 24 : INITIAL_PRODUCT_COUNT,
    sort: "newest",
    search: qNorm || undefined,
  });
  const { data: tree = [] } = useCategoryTree();
  const { data: brands = [] } = useBrands();

  const allCategories = useMemo(() => flattenCategoryTree(tree), [tree]);

  const l1Suggestions = useMemo(() => {
    return FINAL_L1_CATEGORIES.map((c) => {
      const icon =
        CATEGORY_ICON_BY_SLUG[c.iconSlug] ??
        CATEGORY_ICON_BY_SLUG[c.slug] ??
        null;
      const live = tree.find((r) => {
        const n = normalize(r.name);
        return (
          n === normalize(c.name) ||
          c.aliases.some((a) => n === normalize(a) || n.includes(normalize(a)))
        );
      });
      const href = live
        ? categoryHref(live)
        : c.slug
          ? `/categories/${c.slug}`
          : `/catalog?search=${encodeURIComponent(c.name)}`;
      return {
        key: c.key,
        name: c.name,
        href,
        icon: icon ?? resolveCategoryIconUrl({ name: c.name, slug: c.slug }),
      };
    });
  }, [tree]);

  const products = productsQuery.data?.data ?? [];

  const rankedProducts = useMemo(() => {
    if (!qNorm) return products.slice(0, INITIAL_PRODUCT_COUNT);
    return [...products]
      .map((p) => ({ p, s: scoreProduct(p, qNorm) }))
      .sort((a, b) => b.s - a.s)
      .slice(0, SEARCH_PRODUCT_COUNT)
      .map((x) => x.p);
  }, [products, qNorm]);

  /** Only when typing: match L1/L2/L3 (not shown as idle suggestions). */
  const matchedCategories = useMemo(() => {
    if (!qNorm) return [];
    return allCategories
      .filter((c) => normalize(c.name).includes(qNorm))
      .slice(0, SEARCH_CATEGORY_COUNT);
  }, [allCategories, qNorm]);

  /** Only when typing: brands (not shown as idle suggestions). */
  const matchedBrands = useMemo(() => {
    if (!qNorm) return [];
    return (brands ?? [])
      .filter((b) => normalize(b.name).includes(qNorm))
      .slice(0, SEARCH_BRAND_COUNT);
  }, [brands, qNorm]);

  type Row =
    | { kind: "product"; id: string; product: ProductSummary }
    | { kind: "category"; id: string; name: string; href: string; icon?: string | null }
    | { kind: "brand"; id: string; name: string; href: string }
    | { kind: "action"; id: string; label: string; href: string };

  const rows: Row[] = useMemo(() => {
    const list: Row[] = [];
    rankedProducts.forEach((p) =>
      list.push({ kind: "product", id: `p-${p.id}`, product: p }),
    );
    matchedCategories.forEach((c) =>
      list.push({
        kind: "category",
        id: `c-${c.id}`,
        name: c.name,
        href: categoryHref(c),
        icon: resolveCategoryIconUrl(c),
      }),
    );
    matchedBrands.forEach((b) =>
      list.push({
        kind: "brand",
        id: `b-${b.id}`,
        name: b.name,
        href: b.slug ? `/brands/${b.slug}` : `/catalog?brand=${b.id}`,
      }),
    );
    if (qNorm) {
      list.push({
        kind: "action",
        id: "all",
        label: `مشاهده همه نتایج «${toPersianDigits(qNorm)}»`,
        href: `/catalog?search=${encodeURIComponent(qNorm)}`,
      });
    }
    return list;
  }, [rankedProducts, matchedCategories, matchedBrands, qNorm]);

  /** Keyboard rows: on idle, L1 grid cells come first then product list. */
  const keyboardTargets = useMemo(() => {
    if (!isInitial) return rows;
    const l1Rows: Row[] = l1Suggestions.map((c) => ({
      kind: "category" as const,
      id: `l1-${c.key}`,
      name: c.name,
      href: c.href,
      icon: c.icon,
    }));
    return [...l1Rows, ...rows];
  }, [isInitial, l1Suggestions, rows]);

  useEffect(() => {
    if (!open) return;
    setQuery(initialQuery);
    setActiveIndex(0);
    const t = window.setTimeout(() => inputRef.current?.focus(), 40);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.clearTimeout(t);
      document.body.style.overflow = prev;
    };
  }, [open, initialQuery]);

  useEffect(() => {
    setActiveIndex(0);
  }, [debounced]);

  const go = useCallback(
    (href: string) => {
      onClose();
      router.push(href);
    },
    [onClose, router],
  );

  const activate = useCallback(
    (row: Row) => {
      if (row.kind === "product") go(productPath(row.product));
      else go(row.href);
    },
    [go],
  );

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      e.preventDefault();
      onClose();
      return;
    }
    const max = Math.max(keyboardTargets.length - 1, 0);
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, max));
      return;
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
      return;
    }
    if (e.key === "Enter") {
      e.preventDefault();
      const row = keyboardTargets[activeIndex];
      if (row) activate(row);
      else if (qNorm) go(`/catalog?search=${encodeURIComponent(qNorm)}`);
    }
  };

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          className="fixed inset-0 z-[100] flex items-start justify-center overflow-y-auto overscroll-contain p-3 pt-[max(0.75rem,env(safe-area-inset-top))] pb-[max(0.75rem,env(safe-area-inset-bottom))] sm:items-center sm:p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
        >
          <button
            type="button"
            aria-label="بستن جستجو"
            className="fixed inset-0 bg-black/55 md:bg-black/45 md:backdrop-blur-xl md:supports-[backdrop-filter]:bg-black/35"
            onClick={onClose}
          />

          <motion.div
            role="dialog"
            aria-modal
            aria-label="جستجوی کارزار"
            initial={{ opacity: 0, y: 8, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 6, scale: 0.98 }}
            transition={{ type: "spring", stiffness: 420, damping: 34 }}
            className="relative z-10 my-auto flex max-h-[min(calc(100dvh-1.5rem),680px)] w-full max-w-[640px] flex-col overflow-hidden rounded-[1.35rem] bg-white shadow-[0_24px_80px_rgba(0,0,0,0.35)] ring-1 ring-black/5 md:bg-white/82 md:ring-white/60 md:backdrop-blur-2xl md:supports-[backdrop-filter]:bg-white/70"
            onKeyDown={onKeyDown}
          >
            {/* Input row — Spotlight style */}
            <div className="flex shrink-0 items-center gap-3 px-4 py-3.5 sm:px-5 sm:py-4">
              <span className="text-steel/70">
                <Search set="light" size={22} />
              </span>
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="جستجوی ابزار، برند، کد کالا…"
                className="min-w-0 flex-1 bg-transparent text-[17px] font-medium text-foreground outline-none placeholder:font-normal placeholder:text-steel/45"
                autoComplete="off"
                spellCheck={false}
              />
              {query ? (
                <button
                  type="button"
                  onClick={() => setQuery("")}
                  className="rounded-full bg-steel/10 px-2.5 py-1 text-[11px] font-bold text-steel hover:bg-steel/15"
                >
                  پاک
                </button>
              ) : (
                <kbd className="hidden rounded-md bg-steel/8 px-2 py-1 text-[10px] font-bold text-steel/60 sm:inline">
                  ESC
                </kbd>
              )}
            </div>

            <div className="h-px shrink-0 bg-black/[0.06]" />

            <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
              {/* Idle: 12 L1 categories — 2 × 6 on desktop with contained hero icons */}
              {isInitial ? (
                <div className="border-b border-black/[0.05] px-3 py-3 sm:px-4 sm:py-3.5">
                  <p className="mb-2.5 px-1 text-[11px] font-bold text-steel/70">
                    دسته‌بندی‌های اصلی
                  </p>
                  <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 sm:gap-2.5 md:grid-cols-6">
                    {l1Suggestions.map((c, i) => {
                      const active = i === activeIndex;
                      return (
                        <button
                          key={c.key}
                          type="button"
                          onMouseEnter={() => setActiveIndex(i)}
                          onClick={() => go(c.href)}
                          className={cn(
                            "flex min-w-0 flex-col items-center gap-1.5 rounded-2xl px-1 py-2 transition sm:gap-2 sm:px-1.5 sm:py-2.5",
                            active ? "bg-primary/10" : "hover:bg-black/[0.04]",
                          )}
                        >
                          <span
                            className={cn(
                              "relative grid aspect-square h-12 w-12 shrink-0 place-items-center overflow-hidden rounded-full bg-white shadow-soft ring-1 ring-black/[0.06] sm:h-[3.3rem] sm:w-[3.3rem]",
                              active && "ring-2 ring-primary/35",
                            )}
                          >
                            <CategoryVisualIcon
                              icon={c.icon}
                              size={46}
                              color="#5E5F5E"
                              imgClassName="object-contain object-center p-px"
                              alt=""
                            />
                          </span>
                          <span className="line-clamp-2 min-h-[2.4em] w-full text-center text-[9px] font-bold leading-snug text-foreground sm:text-[10px]">
                            {c.name}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              ) : null}

              <div className="py-1.5">
                {isInitial && rankedProducts.length > 0 ? (
                  <p className="mb-1 px-4 text-[11px] font-bold text-steel/70 sm:px-5">
                    محصولات پرفروش
                  </p>
                ) : null}

                {productsQuery.isLoading && qNorm ? (
                  <p className="px-5 py-8 text-center text-sm text-steel">در حال جستجو…</p>
                ) : !isInitial && rows.length === 0 ? (
                  <p className="px-5 py-8 text-center text-sm text-steel">
                    نتیجه‌ای پیدا نشد — عبارت دیگری امتحان کنید
                  </p>
                ) : (
                  rows.map((row, i) => {
                    const rowIndex = isInitial ? l1Suggestions.length + i : i;
                    const active = rowIndex === activeIndex;
                    if (row.kind === "product") {
                      const p = row.product;
                      return (
                        <button
                          key={row.id}
                          type="button"
                          onMouseEnter={() => setActiveIndex(rowIndex)}
                          onClick={() => activate(row)}
                          className={cn(
                            "flex w-full items-center gap-3 px-3 py-2 text-start transition sm:px-4",
                            active ? "bg-primary/10" : "hover:bg-black/[0.03]",
                          )}
                        >
                          <span
                            className={cn(
                              "relative grid h-12 w-12 shrink-0 place-items-center overflow-hidden rounded-[12px] bg-[#F2F2F2]",
                              active && "ring-2 ring-primary/30",
                            )}
                          >
                            {p.thumbnail ? (
                              <SafeImage
                                src={p.thumbnail}
                                alt=""
                                fill
                                className="object-contain p-1"
                                sizes="48px"
                                fallback={<Buy set="bold" primaryColor="#5E5F5E" size={18} />}
                              />
                            ) : (
                              <Buy set="bold" primaryColor="#5E5F5E" size={18} />
                            )}
                          </span>
                          <span className="min-w-0 flex-1">
                            <span className="block truncate text-[13px] font-bold text-foreground sm:text-sm">
                              {p.name}
                            </span>
                            <span className="mt-0.5 flex flex-wrap items-center gap-x-2 text-[11px] text-steel">
                              {p.brand?.name ? <span>{p.brand.name}</span> : null}
                              {p.sku ? (
                                <span dir="ltr" className="opacity-70">
                                  {p.sku}
                                </span>
                              ) : null}
                            </span>
                          </span>
                          <span className="shrink-0 text-xs font-black text-foreground tnum">
                            {p.base_price != null ? formatToman(p.base_price) : "استعلام"}
                          </span>
                        </button>
                      );
                    }

                    if (row.kind === "action") {
                      return (
                        <button
                          key={row.id}
                          type="button"
                          onMouseEnter={() => setActiveIndex(rowIndex)}
                          onClick={() => activate(row)}
                          className={cn(
                            "mx-3 my-1 flex w-[calc(100%-1.5rem)] items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-bold transition sm:mx-4 sm:w-[calc(100%-2rem)]",
                            active
                              ? "bg-primary text-white"
                              : "bg-black/[0.04] text-primary hover:bg-primary/10",
                          )}
                        >
                          <Search size="small" set="bold" />
                          {row.label}
                        </button>
                      );
                    }

                    return (
                      <button
                        key={row.id}
                        type="button"
                        onMouseEnter={() => setActiveIndex(rowIndex)}
                        onClick={() => activate(row)}
                        className={cn(
                          "flex w-full items-center gap-3 px-3 py-2.5 text-start transition sm:px-4",
                          active ? "bg-primary/10" : "hover:bg-black/[0.03]",
                        )}
                      >
                        <span className="grid h-10 w-10 shrink-0 place-items-center overflow-hidden rounded-xl bg-steel/10 text-steel">
                          {row.kind === "category" && row.icon ? (
                            <CategoryVisualIcon icon={row.icon} size={20} color="#5E5F5E" alt="" />
                          ) : (
                            <Category set="bold" size={18} />
                          )}
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-bold text-foreground">
                            {row.name}
                          </span>
                          <span className="text-[11px] text-steel">
                            {row.kind === "brand" ? "برند" : "دسته‌بندی"}
                          </span>
                        </span>
                      </button>
                    );
                  })
                )}
              </div>
            </div>

            <div className="flex shrink-0 items-center justify-end border-t border-black/[0.05] px-4 py-2.5 text-[10px] sm:px-5">
              <Link
                href="/catalog"
                onClick={onClose}
                className="font-bold text-primary hover:underline"
              >
                فروشگاه کارزار
              </Link>
            </div>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
