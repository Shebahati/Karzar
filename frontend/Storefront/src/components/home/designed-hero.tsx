"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronLeft, ChevronRight } from "react-iconly";
import { HeroCategoryOrbs } from "@/components/home/hero-category-orbs";
import {
  featuredOrbs,
  HERO_ORB_CATEGORIES,
  orbsFromPublishedDock,
  orbsFromRoots,
} from "@/config/hero-orbs";
import { composeHeroForMobile, type MobileComposePreset } from "@/lib/mobile-hero-compose";
import { cn } from "@/lib/utils";
import type { CategoryTreeNode } from "@/types/category";
import type { DesignedHeroConfig, DesignedHeroPack, DesignedHeroSlide } from "@/types/hero-design";

const AUTOPLAY_MS = 5500;
const SWIPE_THRESHOLD = 48;
const easePremium = [0.22, 1, 0.36, 1] as const;

function overlayCss(config: DesignedHeroConfig): string {
  const o = config.overlay;
  if (o.mode === "solid") return o.solidColor;
  return `linear-gradient(${o.gradientAngle}deg, ${o.gradientFrom}, ${o.gradientTo})`;
}

function Layer({
  x,
  y,
  className,
  style,
  children,
}: {
  x: number;
  y: number;
  className?: string;
  style?: CSSProperties;
  children: ReactNode;
}) {
  return (
    <div className={cn("absolute z-20", className)} style={{ insetInlineStart: `${x}%`, top: `${y}%`, ...style }}>
      {children}
    </div>
  );
}

function BadgeLive({ badge }: { badge: DesignedHeroConfig["badges"][number] }) {
  const base = "max-w-[220px] shadow-elevated";
  if (badge.style === "chip") {
    return (
      <div
        className={cn(
          base,
          "rounded-full border border-white/25 bg-white/15 px-3 py-1.5 text-white backdrop-blur-md",
        )}
      >
        <span className="text-xs font-bold">{badge.label}</span>
      </div>
    );
  }
  return (
    <div
      className={cn(base, "rounded-full px-3 py-1.5 text-white")}
      style={{ background: "linear-gradient(135deg,#D02327,#a41a1f)" }}
    >
      <span className="text-xs font-bold">{badge.label}</span>
    </div>
  );
}

function SlideCanvas({
  slide,
  reducedMotion,
  blurred,
  mobilePreset,
  isMobile,
}: {
  slide: DesignedHeroSlide;
  reducedMotion: boolean;
  blurred?: boolean;
  mobilePreset?: MobileComposePreset | null;
  isMobile?: boolean;
}) {
  const composed =
    isMobile && mobilePreset ? composeHeroForMobile(slide.config, mobilePreset) : null;
  const config = composed?.config ?? slide.config;
  const overlayOpacity = composed?.overlayOpacity ?? config.overlay.opacity;
  const anim =
    reducedMotion || config.animation === "none" || blurred ? "" : `hero-anim-${config.animation}`;

  const bgSrc =
    config.background.mode === "image"
      ? config.background.imageUrl || "/images/hero/karzar-metrology-lab.jpg"
      : null;

  return (
    <div
      className={cn(
        "absolute inset-0 transition-[opacity,transform] duration-300 ease-out will-change-transform",
        blurred && "scale-[1.015] opacity-40",
      )}
      data-mobile-preset={isMobile ? mobilePreset ?? undefined : undefined}
    >
      {config.background.mode === "color" || !bgSrc ? (
        <div className="absolute inset-0" style={{ background: config.background.color }} />
      ) : (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={bgSrc}
          alt=""
          className="absolute inset-0 h-full w-full object-cover"
          style={{ objectPosition: config.background.focal || "center" }}
        />
      )}

      <div
        className="absolute inset-0"
        style={{ background: overlayCss(config), opacity: overlayOpacity }}
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_80%_0%,rgba(208,35,39,0.2),transparent_42%)]"
      />

      <div className={cn("absolute inset-0", anim, blurred && "opacity-40")}>
        <Layer
          x={config.typography.position.x}
          y={config.typography.position.y}
          style={{
            width: config.typography.maxWidth,
            maxWidth: "92%",
            textAlign:
              config.typography.align === "start"
                ? "right"
                : config.typography.align === "end"
                  ? "left"
                  : "center",
          }}
        >
          <h1
            className="font-black leading-[1.15] tracking-tight"
            style={{
              color: config.typography.titleColor,
              fontSize: `clamp(1.45rem, 4.2vw, ${config.typography.titleSize}px)`,
              textShadow: "0 2px 16px rgba(0,0,0,0.55)",
            }}
          >
            {config.typography.title}
          </h1>
          <div className="mt-2 h-1 w-12 rounded-full bg-primary" />
          <p
            className="mt-3 max-w-prose font-medium leading-relaxed"
            style={{
              color: config.typography.subtitleColor,
              fontSize: `clamp(0.85rem, 1.6vw, ${config.typography.subtitleSize}px)`,
              textShadow: "0 1px 10px rgba(0,0,0,0.45)",
            }}
          >
            {config.typography.subtitle}
          </p>
        </Layer>

        {config.buttons.map((button, i) => {
          const preset =
            button.stylePreset ?? (button.variant === "glass" ? "on-dark-glass" : "primary");
          const size = button.sizePreset ?? "md";
          const pad =
            size === "sm"
              ? "px-3.5 py-2 text-xs"
              : size === "lg"
                ? "px-5 py-3 text-sm sm:text-base"
                : size === "pill"
                  ? "rounded-full px-5 py-2.5 text-sm"
                  : "px-4 py-2.5 text-sm";
          const visual: CSSProperties =
            preset === "soft"
              ? { background: "#5E5F5E", color: "#fff" }
              : preset === "on-dark-glass"
                ? {
                    background: "rgba(255,255,255,0.14)",
                    color: "#fff",
                    backdropFilter: "blur(12px)",
                  }
                : preset === "on-dark-outline"
                  ? {
                      background: "transparent",
                      color: "#fff",
                      border: "1.5px solid rgba(255,255,255,0.55)",
                    }
                  : { background: "#D02327", color: "#fff" };
          const href = button.action.type === "href" ? button.action.value : "/catalog";
          return (
            <Layer
              key={button.id}
              x={button.position.x}
              y={button.position.y}
              className={cn(config.animation === "stagger-up" && `hero-stagger-${Math.min(i + 2, 4)}`)}
            >
              <Link
                href={href}
                className={cn(
                  "inline-block font-bold whitespace-nowrap shadow-[0_8px_24px_rgba(0,0,0,0.22)] transition hover:opacity-95 active:scale-[0.98]",
                  pad,
                  size !== "pill" && "rounded-xl",
                )}
                style={visual}
              >
                {button.label}
              </Link>
            </Layer>
          );
        })}

        {config.badges.map((badge) => (
          <Layer key={badge.id} x={badge.position.x} y={badge.position.y}>
            <BadgeLive badge={badge} />
          </Layer>
        ))}

        {config.carousel?.enabled ? (
          <Layer
            x={config.carousel.position.x}
            y={config.carousel.position.y}
            className={cn(
              "w-[min(360px,72vw)]",
              config.carousel.layoutPreset === "row-large" && "w-[min(440px,82vw)]",
              config.carousel.layoutPreset === "row-compact" && "w-[min(280px,68vw)]",
              config.carousel.layoutPreset === "stack" && "w-[min(220px,60vw)]",
            )}
          >
            <div
              className={cn(
                "rounded-2xl p-3 shadow-[0_12px_36px_rgba(0,0,0,0.28)]",
                (config.carousel.stylePreset ?? "rail-soft") === "cards-elevated" &&
                  "bg-white text-ink",
                (config.carousel.stylePreset ?? "rail-soft") === "rail-soft" &&
                  "bg-white/14 text-white",
                (config.carousel.stylePreset ?? "rail-soft") === "strip-minimal" &&
                  "bg-transparent text-white",
                (config.carousel.stylePreset ?? "rail-soft") === "spotlight" &&
                  "bg-white/16 text-white",
              )}
            >
              <div className="mb-2 flex items-center justify-between gap-2">
                <span className="text-xs font-bold sm:text-sm">
                  {config.carousel.categoryLabel || "محصولات"}
                </span>
                <Link
                  href={
                    config.carousel.categorySlug
                      ? `/categories/${config.carousel.categorySlug}`
                      : "/catalog"
                  }
                  className="rounded-full bg-primary px-2.5 py-0.5 text-[10px] font-bold text-white"
                >
                  بیشتر
                </Link>
              </div>
              <div
                className={cn(
                  "flex gap-2 overflow-x-auto pb-1",
                  config.carousel.layoutPreset === "stack" && "flex-col",
                )}
              >
                {(config.carousel.previewTitles?.length
                  ? config.carousel.previewTitles
                  : Array.from({ length: config.carousel.maxItems }, (_, i) => `محصول ${i + 1}`)
                )
                  .slice(0, config.carousel.maxItems)
                  .map((title, ti) => (
                    <Link
                      key={`${title}-${ti}`}
                      href="/catalog"
                      className={cn(
                        "min-w-[96px] shrink-0 rounded-xl p-2 transition hover:opacity-90",
                        (config.carousel.stylePreset ?? "rail-soft") === "cards-elevated"
                          ? "bg-[#F3F3F3] text-ink"
                          : "bg-white/92 text-ink",
                        (config.carousel.stylePreset ?? "rail-soft") === "spotlight" &&
                          ti === 0 &&
                          "min-w-[124px]",
                      )}
                    >
                      <div className="mb-2 aspect-[4/3] rounded-lg bg-[#E8E8E8]" />
                      <div className="line-clamp-2 text-[10px] font-bold leading-snug">{title}</div>
                    </Link>
                  ))}
              </div>
            </div>
          </Layer>
        ) : null}
      </div>
    </div>
  );
}

export function DesignedHero({
  pack,
  roots = [],
  menuOpen: menuOpenProp,
  onMenuOpenChange,
}: {
  pack: DesignedHeroPack;
  roots?: CategoryTreeNode[];
  menuOpen?: boolean;
  onMenuOpenChange?: (open: boolean) => void;
}) {
  const slides = useMemo(
    () =>
      [...pack.slides]
        .filter((s) => s.isActive)
        .sort((a, b) => a.sortOrder - b.sortOrder),
    [pack.slides],
  );

  const hasPublishedDock = Boolean(pack.categoryDock?.categories?.length);

  const orbDefs = useMemo(() => {
    // Admin-published dock is authoritative for membership + featuredOrder 0–4.
    if (pack.categoryDock?.categories?.length) {
      return orbsFromPublishedDock(pack.categoryDock.categories, roots);
    }
    const live = orbsFromRoots(roots, null);
    if (live.length) return live;
    return HERO_ORB_CATEGORIES;
  }, [roots, pack.categoryDock?.categories]);

  const [index, setIndex] = useState(0);
  const [direction, setDirection] = useState(1);
  const [paused, setPaused] = useState(false);
  const [internalMenu, setInternalMenu] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const touchStartX = useRef<number | null>(null);
  const regionRef = useRef<HTMLElement>(null);

  const menuOpen = menuOpenProp ?? internalMenu;
  const setMenuOpen = onMenuOpenChange ?? setInternalMenu;

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReducedMotion(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    const update = () => setIsMobile(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);

  const activeIndex = slides.length
    ? ((index % slides.length) + slides.length) % slides.length
    : 0;
  const slide = slides[activeIndex];

  const mobilePreset = (
    slide?.mobilePreset ??
    pack.mobilePreset ??
    "balanced"
  ) as MobileComposePreset;

  const go = useCallback(
    (next: number, dir: number) => {
      if (!slides.length) return;
      setDirection(dir);
      setIndex(((next % slides.length) + slides.length) % slides.length);
    },
    [slides.length],
  );

  const goNext = useCallback(() => go(activeIndex + 1, 1), [go, activeIndex]);
  const goPrev = useCallback(() => go(activeIndex - 1, -1), [go, activeIndex]);
  const goTo = useCallback(
    (i: number) => {
      if (i === activeIndex) return;
      go(i, i > activeIndex ? 1 : -1);
    },
    [go, activeIndex],
  );

  useEffect(() => {
    if (slides.length <= 1 || paused || reducedMotion || menuOpen) return;
    const t = window.setInterval(() => {
      setDirection(1);
      setIndex((i) => (i + 1) % slides.length);
    }, AUTOPLAY_MS);
    return () => window.clearInterval(t);
  }, [slides.length, paused, reducedMotion, menuOpen]);

  if (!slide) return null;

  const featuredRaw = featuredOrbs(orbDefs as typeof HERO_ORB_CATEGORIES);
  // When pack ships a dock, honor featuredOrder exactly (no silent first-5 fallback).
  const featured = featuredRaw.length
    ? featuredRaw
    : hasPublishedDock
      ? []
      : (orbDefs as typeof HERO_ORB_CATEGORIES).slice(0, 5);
  const orbActive = (() => {
    const key = slide.config.linkedOrbKey;
    if (key) {
      const idx = featured.findIndex((o) => o.key === key);
      if (idx >= 0) return idx;
    }
    return Math.min(activeIndex, Math.max(0, featured.length - 1));
  })();

  const selectFeatured = (i: number) => {
    const orb = featured[i];
    if (!orb) return;
    const byLink = slides.findIndex((s) => s.config.linkedOrbKey === orb.key);
    goTo(byLink >= 0 ? byLink : Math.min(i, slides.length - 1));
  };

  return (
    <section
      ref={regionRef}
      tabIndex={0}
      aria-roledescription="carousel"
      aria-label="هیرو کارزار"
      className="relative h-[62dvh] w-full outline-none md:h-[100dvh]"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onTouchStart={(e) => {
        touchStartX.current = e.changedTouches[0]?.clientX ?? null;
        setPaused(true);
      }}
      onTouchEnd={(e) => {
        const start = touchStartX.current;
        touchStartX.current = null;
        setPaused(false);
        if (menuOpen || start == null) return;
        const dx = (e.changedTouches[0]?.clientX ?? start) - start;
        if (Math.abs(dx) < SWIPE_THRESHOLD) return;
        if (dx > 0) goNext();
        else goPrev();
      }}
    >
      <div className="relative h-full w-full overflow-hidden">
        <AnimatePresence initial={false} custom={direction}>
          <motion.div
            key={slide.id}
            custom={direction}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: reducedMotion ? 0.18 : 0.75, ease: easePremium }}
            className="absolute inset-0"
          >
            <SlideCanvas
              slide={slide}
              reducedMotion={reducedMotion}
              blurred={menuOpen}
              mobilePreset={mobilePreset}
              isMobile={isMobile}
            />
          </motion.div>
        </AnimatePresence>

        {slides.length > 1 && !menuOpen ? (
          <div className="pointer-events-none absolute inset-x-0 top-[calc(5.5rem+env(safe-area-inset-top,0px))] z-30 flex items-center justify-end gap-2 px-4 sm:px-8">
            <div className="pointer-events-auto flex gap-2" dir="ltr">
              <button
                type="button"
                aria-label="اسلاید بعدی"
                onClick={goNext}
                className="grid h-10 w-10 place-items-center rounded-full bg-black/30 text-white transition hover:bg-black/45 active:scale-95"
              >
                <ChevronLeft set="light" size="small" />
              </button>
              <button
                type="button"
                aria-label="اسلاید قبلی"
                onClick={goPrev}
                className="grid h-10 w-10 place-items-center rounded-full bg-black/30 text-white transition hover:bg-black/45 active:scale-95"
              >
                <ChevronRight set="light" size="small" />
              </button>
            </div>
          </div>
        ) : null}

        {!isMobile ? (
          <HeroCategoryOrbs
            activeIndex={orbActive}
            onSelectFeatured={selectFeatured}
            roots={roots}
            defs={orbDefs as typeof HERO_ORB_CATEGORIES}
            menuOpen={menuOpen}
            onMenuOpenChange={setMenuOpen}
            dockScale="md"
            dockFadeTall={false}
            respectFeaturedOnly={hasPublishedDock}
          />
        ) : null}
      </div>
    </section>
  );
}
