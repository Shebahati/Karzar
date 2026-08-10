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

/**
 * Dock bottom clearance: tablet keeps MobileBottomNav (~4.85rem) + lift;
 * desktop (no bottom nav) uses clamp baseline. +20px raises the dock vs prior sit.
 * Phone dock is `hidden` — mobile categories live below the hero.
 */
const DOCK_BOTTOM_CLEARANCE =
  "pb-[calc(4.85rem+env(safe-area-inset-bottom,0px))] md:pb-[calc(4.85rem+clamp(1.15rem,2.2vw,1.875rem)+20px+env(safe-area-inset-bottom,0px))] lg:pb-[calc(clamp(2.25rem,1.2vw+1.9rem,2.75rem)+20px+env(safe-area-inset-bottom,0px))]";

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
  // Dock md: prior net ~×1.19, then ×1.15 visibility pass. Circle/icon/label/gaps share ratio.
  const disc =
    size === "lg"
      ? "h-[4.75rem] w-[4.75rem] sm:h-[5.25rem] sm:w-[5.25rem]"
      : size === "sm"
        ? "h-[3.76rem] w-[3.76rem]"
        : "h-[4.79rem] w-[4.79rem] sm:h-[5.13rem] sm:w-[5.13rem]";
  const iconSize = size === "lg" ? 34 : size === "sm" ? 33 : 41;
  /** Another +30% on hero only (2.015 × 1.3 ≈ 2.62); circles stay the same. */
  const heroOverflowScale = 2.62;
  const resolvedIcon =
    resolveCategoryIconUrl({ name: orb.name, icon: orb.icon }) ?? orb.icon;

  // Soft under-glow: warm/white lift; red ambient only on selected / accent / idle grid.
  const glowGlass =
    "shadow-[0_6px_18px_rgba(255,255,255,0.34),0_14px_36px_rgba(148,163,184,0.16)]";
  const glowGlassHover =
    "group-hover:shadow-[0_10px_26px_rgba(255,255,255,0.46),0_20px_48px_rgba(148,163,184,0.22)]";
  const glowIdle =
    "shadow-[0_6px_18px_rgba(255,255,255,0.36),0_14px_36px_rgba(208,35,39,0.16)]";
  const glowIdleHover =
    "group-hover:shadow-[0_10px_26px_rgba(255,255,255,0.48),0_20px_48px_rgba(208,35,39,0.26)]";
  const glowSelected =
    "shadow-[0_8px_22px_rgba(255,250,248,0.42),0_18px_44px_rgba(208,35,39,0.38)]";
  const glowSelectedHover =
    "group-hover:shadow-[0_12px_30px_rgba(255,252,250,0.52),0_24px_56px_rgba(208,35,39,0.48)]";
  const glowAccent =
    "shadow-[0_8px_20px_rgba(255,220,218,0.35),0_16px_40px_rgba(208,35,39,0.5)]";
  const glowAccentHover =
    "group-hover:shadow-[0_12px_28px_rgba(255,230,228,0.42),0_22px_52px_rgba(208,35,39,0.58)]";

  const discClass = cn(
    "relative flex items-center justify-center overflow-visible rounded-full will-change-transform",
    // Slightly longer ease so slide/selection sync reads clearly without feeling snappy.
    "transition-[transform,background-color,box-shadow,opacity] duration-[380ms] ease-[cubic-bezier(0.22,1,0.36,1)]",
    disc,
    accent &&
      cn(
        "bg-[#D02327]",
        glowAccent,
        "group-hover:scale-[1.07] group-hover:bg-[#c01f23]",
        glowAccentHover,
        "group-active:scale-[0.96]",
      ),
    // Selected: soft #D02327 wash over brighter glass + clearer lift.
    !accent &&
      selected &&
      cn(
        "scale-[1.15] bg-[color-mix(in_srgb,#D02327_18%,rgba(255,255,255,0.86))] opacity-100",
        glowSelected,
        "group-hover:scale-[1.2] group-hover:bg-[color-mix(in_srgb,#D02327_24%,rgba(255,255,255,0.9))]",
        glowSelectedHover,
      ),
    // Idle (overlay grid): brighter glassy disc + light red tint + soft under-glow.
    !accent &&
      !selected &&
      !dimmed &&
      cn(
        "bg-[color-mix(in_srgb,#D02327_8%,rgba(255,255,255,0.72))]",
        glowIdle,
        "group-hover:scale-[1.09] group-hover:bg-[color-mix(in_srgb,#D02327_12%,rgba(255,255,255,0.82))]",
        glowIdleHover,
      ),
    // Dimmed dock siblings: ~0.82 opacity, steel/gray glass (no red), hover → brighter glass.
    !accent &&
      dimmed &&
      !selected &&
      cn(
        "scale-[0.95] bg-[color-mix(in_srgb,#94a3b8_14%,rgba(255,255,255,0.62))] opacity-[0.82]",
        glowGlass,
        "group-hover:scale-[1.05] group-hover:bg-[color-mix(in_srgb,#94a3b8_10%,rgba(255,255,255,0.78))] group-hover:opacity-[0.94]",
        glowGlassHover,
      ),
  );

  // Fixed 2-line slot so short/long names keep orb discs on one baseline (nav items-end).
  const labelClass = cn(
    "mt-3.5 max-w-[6.5rem] text-center text-[14px] font-semibold leading-snug tracking-tight sm:max-w-[7.53rem] sm:text-[15px]",
    "line-clamp-2 min-h-[2.75em]", // 2 × leading-snug; ellipsis only past 2 lines
    size === "sm" && "mt-2.5 max-w-[5.4rem] text-[11.5px] sm:max-w-[5.87rem] sm:text-[12.5px]",
    size === "lg" && "mt-2.5 max-w-[4.75rem] text-[10px] sm:max-w-[5.5rem] sm:text-[11px]",
    "transition-[opacity,color] duration-[380ms] ease-[cubic-bezier(0.22,1,0.36,1)]",
    accent && "text-white/95 group-hover:text-white",
    !accent && selected && "text-white group-hover:text-white",
    !accent && !selected && !dimmed && "text-white/92 group-hover:text-white",
    !accent && dimmed && !selected && "text-white/82 group-hover:text-white/94",
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
              ? dimmed && !selected
                ? "-translate-y-[6%] drop-shadow-[0_4px_10px_rgba(0,0,0,0.2),0_8px_16px_rgba(148,163,184,0.14)]"
                : "-translate-y-[6%] drop-shadow-[0_4px_10px_rgba(0,0,0,0.22),0_8px_18px_rgba(208,35,39,0.14)]"
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
  roots,
  defs = HERO_ORB_CATEGORIES,
  menuOpen,
  onMenuOpenChange,
  dockScale = "md",
  dockFadeTall = false,
  respectFeaturedOnly = false,
}: {
  /** Passive highlight for the slide’s linked category — clicks navigate, never change slides. */
  activeIndex: number;
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
          DOCK_BOTTOM_CLEARANCE,
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
            // Gaps: prior +40% then ×0.85, then ×1.15 with orbs
            "pointer-events-auto relative mx-auto flex max-w-5xl items-end justify-center overflow-visible gap-[1.71rem] px-4 pt-5 sm:gap-[1.96rem] sm:px-8",
            dockScale === "lg" && "origin-bottom scale-105 gap-[1.96rem] sm:gap-[2.2rem]",
            dockScale === "sm" && "origin-bottom scale-95 gap-[1.22rem] sm:gap-[1.47rem]",
          )}
        >
          {featured.map((orb, i) => {
            const node = matchOrbToTreeNode(orb, roots);
            return (
              <MaterialOrb
                key={orb.key}
                orb={orb}
                href={orbHref(orb, node)}
                size={dockScale === "sm" ? "sm" : "md"}
                selected={i === activeIndex}
                dimmed={i !== activeIndex}
              />
            );
          })}
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
              className="absolute inset-0 bg-black/55 supports-[backdrop-filter]:bg-black/50 md:supports-[backdrop-filter]:bg-black/40 md:supports-[backdrop-filter]:backdrop-blur-[10px]"
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
                  <p className="text-[13px] font-medium tracking-normal text-white/55">کارزار</p>
                  <h2 className="mt-1 text-[1.35rem] font-semibold tracking-normal text-white sm:text-[1.65rem]">
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
