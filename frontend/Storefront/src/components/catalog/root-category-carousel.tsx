"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type MouseEvent as ReactMouseEvent,
  type PointerEvent as ReactPointerEvent,
} from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, ChevronRight } from "react-iconly";
import { useCatalogParams } from "@/components/catalog/use-catalog-params";
import { CategoryVisualIcon } from "@/components/ui/category-visual-icon";
import { Skeleton } from "@/components/ui/skeleton";
import { resolveCategoryIconUrl } from "@/config/category-icons";
import { useCategoryTree, useFlatCategories, useNavGroupDefs } from "@/features/catalog/queries";
import {
  categoryHref,
  isTaxonomyRoot,
  NAV_GROUPS,
  orderedTaxonomyRoots,
} from "@/config/nav-groups";
import { readHorizontalScrollEdges } from "@/lib/scroll-edges";
import { cn, formatNumber } from "@/lib/utils";
import type { CategoryTreeNode } from "@/types/category";

const DRAG_THRESHOLD = 6;

/** Resolve the L1 taxonomy root for a selected category id (itself or ancestor). */
function resolveRootId(
  categoryId: number | undefined,
  flat: { id: number; parent_id: number | null; ancestor_ids?: number[] | null }[] | undefined,
): number | null {
  if (categoryId == null) return null;
  // Until flat taxonomy loads, treat the selected id as the active root so the orb highlights immediately.
  if (!flat?.length) return categoryId;
  const byId = new Map(flat.map((c) => [c.id, c]));
  const cat = byId.get(categoryId);
  if (!cat) return categoryId;
  if (isTaxonomyRoot(cat)) return cat.id;
  for (const aid of cat.ancestor_ids ?? []) {
    const ancestor = byId.get(aid);
    if (ancestor && isTaxonomyRoot(ancestor)) return ancestor.id;
  }
  let current = cat;
  while (current.parent_id != null) {
    const parent = byId.get(current.parent_id);
    if (!parent) break;
    if (isTaxonomyRoot(parent)) return parent.id;
    current = parent;
  }
  return null;
}

function CategoryOrbButton({
  node,
  active,
  onSelect,
  buttonRef,
}: {
  node: CategoryTreeNode;
  active: boolean;
  onSelect: (node: CategoryTreeNode) => void;
  buttonRef?: (el: HTMLButtonElement | null) => void;
}) {
  return (
    <button
      ref={buttonRef}
      type="button"
      aria-pressed={active}
      onClick={() => onSelect(node)}
      className={cn(
        "group flex w-[5.5rem] shrink-0 snap-start flex-col items-center outline-none sm:w-[6.25rem]",
        "focus-visible:rounded-2xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#D02327]/25",
        !active &&
          "hover-fine:[&>span:first-of-type]:bg-karzar-50 hover-fine:[&>span:first-of-type]:text-foreground hover-fine:[&>span:first-of-type]:shadow-[0_8px_18px_-10px_rgba(208,35,39,0.10)]",
      )}
    >
      <span
        className={cn(
          "relative grid h-[4.25rem] w-[4.25rem] place-items-center overflow-visible rounded-full",
          "text-steel transition-[transform,background-color,box-shadow,ring-color,filter] duration-300 ease-out",
          "group-hover:scale-[1.04] group-hover:brightness-[1.03]",
          "sm:h-[4.75rem] sm:w-[4.75rem]",
          active
            ? // Selected: keep gray fill; distinctive soft brand-red ring
              "scale-[1.05] bg-[#F5F5F5] shadow-[0_8px_22px_rgba(208,35,39,0.12)] ring-2 ring-primary/55 group-hover:bg-[#F5F5F5] group-hover:shadow-[0_10px_24px_rgba(208,35,39,0.16)] group-hover:ring-primary/70"
            : "bg-[#F5F5F5] shadow-[0_6px_20px_rgba(0,0,0,0.05)] ring-1 ring-black/[0.04]",
        )}
      >
        <CategoryVisualIcon
          icon={resolveCategoryIconUrl(node) ?? node.icon}
          size={32}
          overflowTop
          color="#5E5F5E"
        />
      </span>
      <span
        className={cn(
          "mt-1.5 max-w-full text-center text-[11px] leading-snug tracking-tight transition-colors duration-300 sm:mt-2.5 sm:text-xs",
          active
            ? "font-black text-foreground group-hover:text-foreground"
            : "font-bold text-foreground/85 group-hover:text-foreground",
        )}
      >
        {node.name}
      </span>
      <span
        className={cn(
          "mt-0.5 text-[10px] transition-colors duration-300",
          active ? "font-bold text-steel" : "font-medium text-steel/80 group-hover:text-steel",
        )}
      >
        {formatNumber(node.product_count ?? 0)} محصول
      </span>
    </button>
  );
}

/**
 * Catalog L1 orbs as a horizontal RTL-aware carousel.
 * Single-select: sets URL `category` → API `category_id`. Second click clears (unless locked).
 *
 * Prefers RSC-passed `initialTree` so SSR HTML matches hydrated client
 * (avoids shimmer ↔ orbs hydration mismatch, same pattern as BrandStrip).
 */
export function RootCategoryCarousel({
  lockedCategoryId,
  initialTree = [],
}: {
  /** Hub pages: force-select this category’s L1 root even before URL sync. */
  lockedCategoryId?: number;
  /** RSC prefetch seed — keeps first paint stable across hydrate. */
  initialTree?: CategoryTreeNode[];
} = {}) {
  const router = useRouter();
  const { data, isLoading } = useCategoryTree();
  const { data: flatCategories } = useFlatCategories();
  const { data: navDefs = NAV_GROUPS } = useNavGroupDefs();
  const { params, setParams } = useCatalogParams();
  const tree = useMemo(
    () => (data?.length ? data : initialTree) ?? [],
    [data, initialTree],
  );
  const roots = useMemo(() => orderedTaxonomyRoots(tree, navDefs), [tree, navDefs]);

  const selectedCategoryId = lockedCategoryId ?? params.category_id;
  const activeRootId = useMemo(
    () => resolveRootId(selectedCategoryId, flatCategories),
    [selectedCategoryId, flatCategories],
  );

  const trackRef = useRef<HTMLDivElement>(null);
  const orbRefs = useRef(new Map<number, HTMLButtonElement>());
  const didScrollToActive = useRef<number | null>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);
  const [hasOverflow, setHasOverflow] = useState(false);

  const dragRef = useRef<{
    pointerId: number;
    startX: number;
    startScroll: number;
    moved: boolean;
    dragging: boolean;
  } | null>(null);
  const suppressClickRef = useRef(false);

  const updateEdges = useCallback(() => {
    const el = trackRef.current;
    if (!el) return;
    const edges = readHorizontalScrollEdges(el);
    setCanScrollLeft(edges.canScrollLeft);
    setCanScrollRight(edges.canScrollRight);
    setHasOverflow(edges.hasOverflow);
  }, []);

  useEffect(() => {
    const el = trackRef.current;
    if (!el) return;
    updateEdges();
    // Layout can settle after fonts/icons; re-measure next frames.
    const raf1 = requestAnimationFrame(() => {
      updateEdges();
      requestAnimationFrame(updateEdges);
    });
    const onScroll = () => updateEdges();
    el.addEventListener("scroll", onScroll, { passive: true });
    const ro = new ResizeObserver(() => updateEdges());
    ro.observe(el);
    // Also watch the first child — content width changes independently of the rail.
    const first = el.firstElementChild;
    if (first) ro.observe(first);
    return () => {
      cancelAnimationFrame(raf1);
      el.removeEventListener("scroll", onScroll);
      ro.disconnect();
    };
  }, [updateEdges, roots.length]);

  // Scroll the URL/locked selected orb into the track only (never document scroll).
  useEffect(() => {
    if (activeRootId == null || !roots.length) return;
    if (didScrollToActive.current === activeRootId) return;
    const btn = orbRefs.current.get(activeRootId);
    const track = trackRef.current;
    if (!btn || !track) return;
    didScrollToActive.current = activeRootId;
    requestAnimationFrame(() => {
      const trackBox = track.getBoundingClientRect();
      const btnBox = btn.getBoundingClientRect();
      const btnCenter = (btnBox.left + btnBox.right) / 2;
      const trackCenter = (trackBox.left + trackBox.right) / 2;
      const delta = btnCenter - trackCenter;
      if (Math.abs(delta) >= 1) {
        track.scrollBy({ left: delta, behavior: "smooth" });
      }
      updateEdges();
    });
  }, [activeRootId, roots.length, updateEdges]);

  const step = useCallback((dir: 1 | -1) => {
    const el = trackRef.current;
    if (!el) return;
    const amount = Math.min(280, Math.max(160, el.clientWidth * 0.65));
    // Chromium already inverts scrollLeft under direction:rtl — do not negate.
    el.scrollBy({ left: dir * amount, behavior: "smooth" });
    // Edges update on scroll event; also nudge after the smooth scroll starts.
    requestAnimationFrame(updateEdges);
  }, [updateEdges]);

  const onPointerDown = (e: ReactPointerEvent<HTMLDivElement>) => {
    // Touch uses native overflow pan; custom drag is mouse/pen only.
    if (e.pointerType === "touch") return;
    if (e.button !== 0) return;
    const el = trackRef.current;
    if (!el) return;
    // A prior drag can set suppress without a following click — never leave it sticky.
    suppressClickRef.current = false;
    dragRef.current = {
      pointerId: e.pointerId,
      startX: e.clientX,
      startScroll: el.scrollLeft,
      moved: false,
      dragging: true,
    };
    // Capture only after the drag threshold so orb button clicks stay reliable.
  };

  const onPointerMove = (e: ReactPointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current;
    const el = trackRef.current;
    if (!drag?.dragging || !el || drag.pointerId !== e.pointerId) return;
    const dx = e.clientX - drag.startX;
    if (!drag.moved && Math.abs(dx) < DRAG_THRESHOLD) return;
    if (!drag.moved) {
      drag.moved = true;
      try {
        el.setPointerCapture(e.pointerId);
      } catch {
        /* ignore */
      }
    }
    // scrollLeft delta matches pointer delta in both LTR and RTL (Chromium).
    el.scrollLeft = drag.startScroll - dx;
  };

  const endDrag = (e: ReactPointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current;
    const el = trackRef.current;
    if (!drag || drag.pointerId !== e.pointerId) return;
    if (drag.moved) suppressClickRef.current = true;
    dragRef.current = null;
    if (el?.hasPointerCapture(e.pointerId)) {
      el.releasePointerCapture(e.pointerId);
    }
    updateEdges();
  };

  const onClickCapture = (e: ReactMouseEvent<HTMLDivElement>) => {
    if (!suppressClickRef.current) return;
    suppressClickRef.current = false;
    e.preventDefault();
    e.stopPropagation();
  };

  const selectRoot = (node: CategoryTreeNode) => {
    // Hub: switching root navigates to that category; cannot clear the lock.
    if (lockedCategoryId != null) {
      if (activeRootId === node.id) return;
      router.push(categoryHref(node));
      return;
    }
    // Toggle off when this root (or a descendant under it) is already active.
    if (activeRootId === node.id) {
      setParams({ category: null, roots: null });
      return;
    }
    // Single select — replace previous; drop legacy multi-root param.
    // Stay on /catalog?category=id so PLP filters in place (hub links still via home/menus).
    setParams({ category: node.id, roots: null });
  };

  // Only shimmer when neither RSC seed nor query data is available.
  if (!roots.length && isLoading) {
    return (
      <div className="flex gap-3 h-scroll no-scrollbar pe-2 pt-2 pb-3 sm:gap-4 sm:pt-3 sm:pb-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="flex w-[5.5rem] shrink-0 flex-col items-center gap-2 sm:w-[6.25rem] sm:gap-2.5">
            <Skeleton className="h-[4.25rem] w-[4.25rem] rounded-full sm:h-[4.75rem] sm:w-[4.75rem]" />
            <Skeleton className="h-3 w-14 rounded-full" />
          </div>
        ))}
      </div>
    );
  }

  if (!roots.length) return null;

  return (
    <div className="min-w-0 w-full">
      {lockedCategoryId == null && activeRootId != null && (
        <div className="mb-1.5 flex items-end justify-end gap-3 sm:mb-3">
          <button
            type="button"
            className="text-xs font-bold text-primary transition-opacity hover:opacity-80"
            onClick={() => setParams({ category: null, roots: null })}
          >
            پاک کردن
          </button>
        </div>
      )}

      {/*
        Vertical padding lives on the scroll rail so scale + soft shadow of the
        selected orb are not clipped. overflow-x:auto forces y to auto in CSS,
        so padding (not overflow-y:visible) is the reliable fix.
        min-w-0 + w-full keeps the rail inside the page column so overflow scrolls
        inside the track instead of expanding the layout.
      */}
      <div className="relative min-w-0 w-full">
        <div
          ref={trackRef}
          aria-label="دسته‌ها"
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={endDrag}
          onPointerCancel={endDrag}
          onClickCapture={onClickCapture}
          className={cn(
            "no-scrollbar h-scroll flex w-full min-w-0 gap-3 overflow-x-auto overflow-y-hidden overscroll-x-contain scroll-smooth px-1 pt-2 pb-3 sm:gap-4 sm:pt-3 sm:pb-5",
            // touch-manipulation: allow vertical page scroll + horizontal rail pan.
            // Avoid touch-pan-x alone (traps vertical gestures on mobile).
            "md:snap-x md:snap-mandatory touch-manipulation select-none",
            "cursor-grab active:cursor-grabbing",
          )}
        >
          {roots.map((node) => (
            <CategoryOrbButton
              key={node.id}
              node={node}
              active={activeRootId === node.id}
              onSelect={selectRoot}
              buttonRef={(el) => {
                if (el) orbRefs.current.set(node.id, el);
                else orbRefs.current.delete(node.id);
              }}
            />
          ))}
        </div>

        {hasOverflow && (
          <>
            {/* Physical right (−start in RTL): only when more content exists toward visual right. */}
            <button
              type="button"
              aria-label="به راست"
              disabled={!canScrollRight}
              onClick={() => step(1)}
              className={cn(
                "absolute -start-1 top-[2.55rem] z-10 hidden h-9 w-9 -translate-y-1/2 place-items-center rounded-full bg-card/95 text-steel shadow-[0_8px_20px_rgba(0,0,0,0.08)] backdrop-blur-sm transition-all duration-300 lg:grid sm:top-[2.8rem]",
                "hover:text-primary disabled:pointer-events-none disabled:opacity-0",
              )}
            >
              <ChevronRight set="light" size="small" />
            </button>
            {/* Physical left (−end in RTL): only when more content exists toward visual left. */}
            <button
              type="button"
              aria-label="به چپ"
              disabled={!canScrollLeft}
              onClick={() => step(-1)}
              className={cn(
                "absolute -end-1 top-[2.55rem] z-10 hidden h-9 w-9 -translate-y-1/2 place-items-center rounded-full bg-card/95 text-steel shadow-[0_8px_20px_rgba(0,0,0,0.08)] backdrop-blur-sm transition-all duration-300 lg:grid sm:top-[2.8rem]",
                "hover:text-primary disabled:pointer-events-none disabled:opacity-0",
              )}
            >
              <ChevronLeft set="light" size="small" />
            </button>
          </>
        )}
      </div>
    </div>
  );
}
