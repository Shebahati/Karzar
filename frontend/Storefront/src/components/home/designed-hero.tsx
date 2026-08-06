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
import { SafeImage } from "@/components/ui/safe-image";
import { composeHeroForMobile, type MobileComposePreset } from "@/lib/mobile-hero-compose";
import { lcpImageProps } from "@/lib/cwv";
import { cn } from "@/lib/utils";
import type { CategoryTreeNode } from "@/types/category";
import type { DesignedHeroConfig, DesignedHeroPack, DesignedHeroSlide } from "@/types/hero-design";

const AUTOPLAY_MS = 5500;
const SWIPE_THRESHOLD = 48;
/** Hard cap — published pack + dock are designed around 6 slides / 5 featured orbs. */
const MAX_ACTIVE_SLIDES = 6;
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

function BadgeLive({
  badge,
  lite,
}: {
  badge: DesignedHeroConfig["badges"][number];
  lite?: boolean;
}) {
  const base = "max-w-[220px] shadow-elevated";
  if (badge.style === "chip") {
    return (
      <div
        className={cn(
          base,
          "rounded-full border border-white/25 bg-white/15 px-3 py-1.5 text-white",
          !lite && "backdrop-blur-md",
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
  priority,
}: {
  slide: DesignedHeroSlide;
  reducedMotion: boolean;
  blurred?: boolean;
  mobilePreset?: MobileComposePreset | null;
  isMobile?: boolean;
  priority?: boolean;
}) {
  const composed =
    isMobile && mobilePreset ? composeHeroForMobile(slide.config, mobilePreset) : null;
  const config = composed?.config ?? slide.config;
  const overlayOpacity = composed?.overlayOpacity ?? config.overlay.opacity;
  // Mobile + reduced-motion: no CSS keyframe layer (esp. infinite float).
  const lite = Boolean(isMobile || reducedMotion);
  const anim =
    lite || config.animation === "none" || blurred ? "" : `hero-anim-${config.animation}`;

  const bgSrc =
    config.background.mode === "image"
      ? config.background.imageUrl || "/images/hero/karzar-metrology-lab.jpg"
      : null;

  return (
    <div
      className={cn(
        "absolute inset-0 transition-[opacity,transform] duration-300 ease-out",
        !lite && "will-change-transform",
        blurred && "scale-[1.015] opacity-40",
      )}
      data-mobile-preset={isMobile ? mobilePreset ?? undefined : undefined}
    >
      {config.background.mode === "color" || !bgSrc ? (
        <div className="absolute inset-0" style={{ background: config.background.color }} />
      ) : (
        <SafeImage
          src={bgSrc}
          alt=""
          fill
          sizes={isMobile ? "100vw" : "(max-width: 1024px) 100vw, 100vw"}
          className="object-cover"
          style={{ objectPosition: config.background.focal || "center" }}
          fallback={<div className="absolute inset-0 bg-[#1a1a1a]" />}
          {...(priority ? lcpImageProps() : { loading: "lazy" as const })}
        />
      )}

      <div
        className="absolute inset-0"
        style={{ background: overlayCss(config), opacity: overlayOpacity }}
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
            className="font-extrabold leading-[1.18] tracking-tight"
            style={{
              color: config.typography.titleColor,
              fontSize: `clamp(1.5rem, 4vw, ${config.typography.titleSize}px)`,
              textShadow: "0 2px 20px rgba(0,0,0,0.45)",
            }}
          >
            {config.typography.title}
          </h1>
          <div
            className="mt-3 h-px w-10"
            style={{ background: "rgba(208,35,39,0.85)" }}
            aria-hidden
          />
          <p
            className="mt-4 max-w-prose font-normal leading-relaxed"
            style={{
              color: config.typography.subtitleColor,
              fontSize: `clamp(0.9rem, 1.55vw, ${config.typography.subtitleSize}px)`,
              textShadow: "0 1px 12px rgba(0,0,0,0.4)",
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
                    background: lite ? "rgba(255,255,255,0.22)" : "rgba(255,255,255,0.14)",
                    color: "#fff",
                    ...(lite ? {} : { backdropFilter: "blur(12px)" }),
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
              className={cn(
                !lite && config.animation === "stagger-up" && `hero-stagger-${Math.min(i + 2, 4)}`,
              )}
            >
              <Link
                href={href}
                className={cn(
                  "inline-block font-semibold whitespace-nowrap transition hover:opacity-95 active:scale-[0.98]",
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
            <BadgeLive badge={badge} lite={lite} />
          </Layer>
        ))}

        {/* Nested product preview rail is desktop-only — heavy DOM on phones. */}
        {!isMobile && config.carousel?.enabled ? (
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
                          : "bg-white/[0.92] text-ink",
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
  const slides = useMemo(() => {
    const seen = new Set<string>();
    return [...pack.slides]
      .filter((s) => s.isActive)
      .sort((a, b) => a.sortOrder - b.sortOrder)
      .filter((s) => {
        if (seen.has(s.id)) return false;
        seen.add(s.id);
        return true;
      })
      .slice(0, MAX_ACTIVE_SLIDES);
  }, [pack.slides]);

  const publishedDockCategories = pack.categoryDock?.categories;
  const hasPublishedDock = Boolean(publishedDockCategories?.length);

  const orbDefs = useMemo(() => {
    // Admin-published dock is authoritative for membership + featuredOrder 0–4.
    if (publishedDockCategories?.length) {
      return orbsFromPublishedDock(publishedDockCategories, roots);
    }
    const live = orbsFromRoots(roots, null);
    if (live.length) return live;
    return HERO_ORB_CATEGORIES;
  }, [roots, publishedDockCategories]);

  const [index, setIndex] = useState(0);
  const [direction, setDirection] = useState(1);
  const [paused, setPaused] = useState(false);
  const [internalMenu, setInternalMenu] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  /** Fine-pointer split: visual left/right half of hero shows only that arrow. */
  const [arrowSide, setArrowSide] = useState<"left" | "right" | null>(null);
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

  const slideCount = slides.length;
  const activeIndex = slideCount
    ? ((index % slideCount) + slideCount) % slideCount
    : 0;
  const slide = slides[activeIndex];

  // Clamp when pack shrinks (e.g. 13 → 6) so we never sit past the last slide.
  useEffect(() => {
    if (!slideCount) return;
    setIndex((i) => ((i % slideCount) + slideCount) % slideCount);
  }, [slideCount]);

  const mobilePreset = (
    slide?.mobilePreset ??
    pack.mobilePreset ??
    "balanced"
  ) as MobileComposePreset;

  const goNext = useCallback(() => {
    if (!slideCount) return;
    setDirection(1);
    setIndex((i) => (i + 1) % slideCount);
  }, [slideCount]);

  const goPrev = useCallback(() => {
    if (!slideCount) return;
    setDirection(-1);
    setIndex((i) => (i - 1 + slideCount) % slideCount);
  }, [slideCount]);

  // Desktop-only autoplay — mobile stays swipe/manual (saves timers + slide churn).
  useEffect(() => {
    if (isMobile || slideCount <= 1 || paused || reducedMotion || menuOpen) return;
    const t = window.setInterval(() => {
      setDirection(1);
      setIndex((i) => (i + 1) % slideCount);
    }, AUTOPLAY_MS);
    return () => window.clearInterval(t);
  }, [isMobile, slideCount, paused, reducedMotion, menuOpen]);

  if (!slide) return null;

  const liteMotion = isMobile || reducedMotion;

  const featuredRaw = featuredOrbs(orbDefs as typeof HERO_ORB_CATEGORIES);
  // When pack ships a dock, honor featuredOrder exactly (no silent first-5 fallback).
  const featured = featuredRaw.length
    ? featuredRaw
    : hasPublishedDock
      ? []
      : (orbDefs as typeof HERO_ORB_CATEGORIES).slice(0, 5);
  /**
   * Passive highlight only — orb clicks navigate to category pages.
   * Match by stable linkedOrbKey (never slide index — that drifts vs 5 dock slots).
   * -1 = no dock highlight (e.g. 6th filler slide).
   */
  const orbActive = (() => {
    const key = slide.config.linkedOrbKey;
    if (!key || !featured.length) return -1;
    return featured.findIndex((o) => o.key === key);
  })();

  const slideArrowClass = (side: "left" | "right") =>
    cn(
      "pointer-events-auto absolute top-1/2 z-30 grid h-11 w-11 -translate-y-1/2 place-items-center rounded-full",
      "bg-black/35 text-white shadow-[0_8px_22px_rgba(0,0,0,0.24)]",
      !isMobile && "backdrop-blur-md",
      "transition-[opacity,background-color,box-shadow] duration-300 ease-out",
      "hover-fine:bg-black/48 hover-fine:shadow-[0_10px_28px_rgba(0,0,0,0.32)]",
      "active:bg-black/55",
      "focus-visible:!opacity-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white/55",
      // Touch / coarse: always slightly visible
      "opacity-40",
      // Fine pointer: hidden unless this visual half is hovered (or focused)
      "[@media(hover:hover)_and_(pointer:fine)]:opacity-0",
      arrowSide === side && "[@media(hover:hover)_and_(pointer:fine)]:!opacity-100",
    );

  return (
    <section
      ref={regionRef}
      tabIndex={0}
      aria-roledescription="carousel"
      aria-label="هیرو کارزار"
      className="group/hero relative h-[62dvh] w-full outline-none md:h-[100dvh]"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => {
        setPaused(false);
        setArrowSide(null);
      }}
      onPointerMove={(e) => {
        if (e.pointerType !== "mouse" && e.pointerType !== "pen") return;
        const rect = e.currentTarget.getBoundingClientRect();
        const next = e.clientX - rect.left < rect.width / 2 ? "left" : "right";
        setArrowSide((prev) => (prev === next ? prev : next));
      }}
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
        // Match L/R buttons: visual-left = next, visual-right = prev (RTL carousel).
        if (dx < 0) goNext();
        else goPrev();
      }}
    >
      <div className="relative h-full w-full overflow-hidden">
        {liteMotion ? (
          // Instant/CSS swap — no Framer layout work on weak phones.
          <div key={slide.id} className="absolute inset-0">
            <SlideCanvas
              slide={slide}
              reducedMotion
              blurred={menuOpen}
              mobilePreset={mobilePreset}
              isMobile={isMobile}
              priority={activeIndex === 0}
            />
          </div>
        ) : (
          <AnimatePresence initial={false} custom={direction}>
            <motion.div
              key={slide.id}
              custom={direction}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.75, ease: easePremium }}
              className="absolute inset-0"
            >
              <SlideCanvas
                slide={slide}
                reducedMotion={false}
                blurred={menuOpen}
                mobilePreset={mobilePreset}
                isMobile={false}
                priority={activeIndex === 0}
              />
            </motion.div>
          </AnimatePresence>
        )}

        {slides.length > 1 && !menuOpen ? (
          <>
            {/* Visual left → next (RTL carousel); physical left/right, not logical start/end */}
            <button
              type="button"
              aria-label="اسلاید بعدی"
              onClick={goNext}
              className={cn(slideArrowClass("left"), "left-3 sm:left-5")}
            >
              <ChevronLeft set="light" size="small" />
            </button>
            <button
              type="button"
              aria-label="اسلاید قبلی"
              onClick={goPrev}
              className={cn(slideArrowClass("right"), "right-3 sm:right-5")}
            >
              <ChevronRight set="light" size="small" />
            </button>
          </>
        ) : null}

        {!isMobile ? (
          <HeroCategoryOrbs
            activeIndex={orbActive}
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
