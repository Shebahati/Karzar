"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CloseSquare } from "react-iconly";
import { CategoryVisualIcon } from "@/components/ui/category-visual-icon";
import { resolveCategoryIconUrl } from "@/config/category-icons";
import { cn } from "@/lib/utils";
import {
  featuredOrbs,
  matchOrbToTreeNode,
  orbHref,
  isDiscountsOrbKey,
  type HeroOrbDef,
  HERO_ORB_CATEGORIES,
} from "@/config/hero-orbs";
import type { CategoryTreeNode } from "@/types/category";

function isOverlayExcludedOrb(orb: Pick<HeroOrbDef, "key" | "name" | "slugHint" | "special">): boolean {
  if (orb.special || isDiscountsOrbKey(orb.key)) return true;
  if (orb.slugHint === "takhfif") return true;
  const n = orb.name.replace(/\u200c/g, "").replace(/\s+/g, " ").trim();
  return n === "تخفیف‌ها" || n === "تخفیف ها" || n === "تخفیف";
}

const springSoft = { type: "spring" as const, stiffness: 420, damping: 36, mass: 0.8 };
const fadeQuick = { duration: 0.22, ease: [0.25, 0.1, 0.25, 1] as const };

/** Matches layout clearance for fixed MobileBottomNav (~4.75rem + safe area). */
const MOBILE_NAV_CLEARANCE =
  "pb-[calc(4.85rem+env(safe-area-inset-bottom,0px))] lg:pb-[max(0.65rem,env(safe-area-inset-bottom,0px))]";

function usePrefersReducedMotion() {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReduced(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);
  return reduced;
}

function MaterialOrb({
  orb,
  href,
  selected,
  dimmed,
  size = "md",
  onClick,
  accent,
}: {
  orb: Pick<HeroOrbDef, "name" | "icon">;
  href?: string;
  selected?: boolean;
  dimmed?: boolean;
  size?: "sm" | "md" | "lg";
  onClick?: () => void;
  accent?: boolean;
}) {
  // Dock md: base×1.4 then ×0.85 (net ~×1.19). Circle/icon/label/gaps share ratio.
  const disc =
    size === "lg"
      ? "h-[4.75rem] w-[4.75rem] sm:h-[5.25rem] sm:w-[5.25rem]"
      : size === "sm"
        ? "h-[3.27rem] w-[3.27rem]"
        : "h-[4.165rem] w-[4.165rem] sm:h-[4.46rem] sm:w-[4.46rem]";
  const iconSize = size === "lg" ? 34 : size === "sm" ? 29 : 36;
  /** Another +30% on hero only (2.015 × 1.3 ≈ 2.62); circles stay the same. */
  const heroOverflowScale = 2.62;
  const resolvedIcon =
    resolveCategoryIconUrl({ name: orb.name, icon: orb.icon }) ?? orb.icon;

  const discClass = cn(
    "relative flex items-center justify-center overflow-visible rounded-full transition-[transform,background-color,box-shadow,opacity] duration-300 ease-out will-change-transform",
    disc,
    accent &&
      "bg-[#D02327] shadow-[0_10px_28px_rgba(208,35,39,0.45)] group-hover:bg-[#b81e23] group-active:scale-[0.96]",
    !accent &&
      selected &&
      "scale-[1.08] bg-white/40 shadow-[0_10px_28px_rgba(0,0,0,0.28)] ring-2 ring-white/55",
    !accent &&
      !selected &&
      !dimmed &&
      "bg-white/[0.26] shadow-[0_6px_18px_rgba(0,0,0,0.2)] ring-1 ring-white/30 group-hover:bg-white/[0.34] group-hover:scale-[1.04]",
    !accent && dimmed && !selected && "bg-white/[0.18] opacity-75 ring-1 ring-white/20 scale-[0.96]",
  );

  // Fixed 2-line slot so short/long names keep orb discs on one baseline (nav items-end).
  const labelClass = cn(
    "mt-3 max-w-[5.65rem] text-center text-[12px] font-semibold leading-snug tracking-tight sm:max-w-[6.55rem] sm:text-[13px]",
    "line-clamp-2 min-h-[2.75em]", // 2 × leading-snug; ellipsis only past 2 lines
    size === "sm" && "mt-2 max-w-[4.7rem] text-[10px] sm:max-w-[5.1rem] sm:text-[11px]",
    size === "lg" && "mt-2.5 max-w-[4.75rem] text-[10px] sm:max-w-[5.5rem] sm:text-[11px]",
    "transition-opacity duration-300",
    accent && "text-white/95",
    !accent && selected && "text-white",
    !accent && !selected && !dimmed && "text-white/80",
    !accent && dimmed && !selected && "text-white/55",
  );

  const inner = (
    <>
      <span className={discClass}>
        <CategoryVisualIcon
          icon={resolvedIcon}
          size={iconSize}
          overflowTop={!accent}
          overflowScale={heroOverflowScale}
          // Dead-center in circle with a tiny upward peek (overrides default −8%).
          imgClassName={
            !accent
              ? "-translate-y-[6%] drop-shadow-[0_6px_12px_rgba(0,0,0,0.28)]"
              : undefined
          }
          color={accent ? "#FFFFFF" : selected ? "#FFFFFF" : "rgba(255,255,255,0.95)"}
        />
      </span>
      <span className={labelClass}>{orb.name}</span>
    </>
  );

  const className = cn(
    "group flex shrink-0 flex-col items-center outline-none",
    "focus-visible:rounded-2xl focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-white/50",
  );

  if (href) {
    return (
      <Link href={href} className={className} onClick={onClick}>
        {inner}
      </Link>
    );
  }

  return (
    <button type="button" className={className} onClick={onClick}>
      {inner}
    </button>
  );
}

export function HeroCategoryOrbs({
  activeIndex,
  onSelectFeatured,
  roots,
  defs = HERO_ORB_CATEGORIES,
  menuOpen,
  onMenuOpenChange,
  dockScale = "md",
  dockFadeTall = false,
  respectFeaturedOnly = false,
}: {
  activeIndex: number;
  onSelectFeatured: (index: number) => void;
  roots: CategoryTreeNode[];
  defs?: HeroOrbDef[];
  menuOpen: boolean;
  onMenuOpenChange: (open: boolean) => void;
  dockScale?: "sm" | "md" | "lg";
  dockFadeTall?: boolean;
  /** When true, never invent a first-5 fallback — honor featuredOrder from pack. */
  respectFeaturedOnly?: boolean;
}) {
  const featuredRaw = featuredOrbs(defs);
  // Never invent a first-5 set when a published dock already decided featuredOrder.
  const featured =
    featuredRaw.length || respectFeaturedOnly ? featuredRaw : defs.slice(0, 5);
  /** All-categories overlay: real L1 only — never show تخفیف‌ها / discounts special. */
  const menuOrbs = defs.filter((orb) => !isOverlayExcludedOrb(orb));
  const reduced = usePrefersReducedMotion();

  return (
    <>
      {/* Desktop / tablet dock only — mobile categories live in home sheet below hero */}
      <div
        className={cn(
          "pointer-events-none absolute inset-x-0 bottom-0 z-40 hidden pt-28 md:block",
          MOBILE_NAV_CLEARANCE,
        )}
      >
        <div
          aria-hidden
          className={cn(
            "pointer-events-none absolute inset-x-0 bottom-0 bg-[linear-gradient(to_top,rgba(0,0,0,0.58)_0%,rgba(0,0,0,0.2)_55%,transparent_100%)]",
            dockFadeTall ? "h-52" : "h-44",
          )}
        />

        <nav
          aria-label="دسته‌های پاور هیرو"
          className={cn(
            // Gaps: prior +40% then ×0.85 together with orbs
            "pointer-events-auto relative mx-auto flex max-w-5xl items-end justify-center overflow-visible gap-[1.49rem] px-4 pt-5 sm:gap-[1.7rem] sm:px-8",
            dockScale === "lg" && "origin-bottom scale-105 gap-[1.7rem] sm:gap-[1.91rem]",
            dockScale === "sm" && "origin-bottom scale-95 gap-[1.06rem] sm:gap-[1.28rem]",
          )}
        >
          {featured.map((orb, i) => (
            <MaterialOrb
              key={orb.key}
              orb={orb}
              size={dockScale === "sm" ? "sm" : "md"}
              selected={i === activeIndex}
              dimmed={i !== activeIndex}
              onClick={() => onSelectFeatured(i)}
            />
          ))}
          <MaterialOrb
            orb={{ name: "همه محصولات", icon: "Category" }}
            size={dockScale === "sm" ? "sm" : "md"}
            accent
            onClick={() => onMenuOpenChange(true)}
          />
        </nav>
      </div>

      <AnimatePresence>
        {menuOpen ? (
          <motion.div
            key="orb-menu"
            className="absolute inset-0 z-50 flex items-center justify-center px-5"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={reduced ? { duration: 0.12 } : fadeQuick}
          >
            <button
              type="button"
              aria-label="بستن منوی دسته‌بندی"
              className="absolute inset-0 bg-black/50 supports-[backdrop-filter]:bg-black/40 supports-[backdrop-filter]:backdrop-blur-[10px]"
              onClick={() => onMenuOpenChange(false)}
            />

            <motion.div
              role="dialog"
              aria-modal
              aria-label="همه دسته‌بندی‌ها"
              className="relative z-10 w-full max-w-3xl"
              initial={reduced ? false : { opacity: 0, scale: 0.96, y: 12 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={reduced ? { opacity: 0 } : { opacity: 0, scale: 0.98, y: 8 }}
              transition={reduced ? { duration: 0.12 } : springSoft}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="mb-8 flex items-start justify-between gap-4 px-1">
                <div>
                  <p className="text-[13px] font-medium tracking-wide text-white/55">کارزار</p>
                  <h2 className="mt-1 text-[1.35rem] font-semibold tracking-tight text-white sm:text-[1.65rem]">
                    همه دسته‌بندی‌ها
                  </h2>
                </div>
                <button
                  type="button"
                  onClick={() => onMenuOpenChange(false)}
                  className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-white/14 text-white transition hover:bg-white/22 active:scale-95"
                  aria-label="بستن"
                >
                  <CloseSquare set="light" size="small" />
                </button>
              </div>

              <div className="grid grid-cols-3 gap-x-2 gap-y-7 sm:grid-cols-6 sm:gap-x-4 sm:gap-y-9">
                {menuOrbs.map((orb, i) => {
                  const node = matchOrbToTreeNode(orb, roots);
                  return (
                    <motion.div
                      key={orb.key}
                      initial={reduced ? false : { opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={
                        reduced
                          ? { duration: 0 }
                          : { ...springSoft, delay: Math.min(i * 0.018, 0.16) }
                      }
                      className="flex justify-center"
                    >
                      <MaterialOrb
                        orb={orb}
                        href={orbHref(orb, node)}
                        size="lg"
                        onClick={() => onMenuOpenChange(false)}
                      />
                    </motion.div>
                  );
                })}
              </div>
            </motion.div>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </>
  );
}
