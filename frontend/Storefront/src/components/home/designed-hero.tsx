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
import { flushSync } from "react-dom";
import Link from "next/link";
import {
  AnimatePresence,
  animate,
  motion,
  useMotionValue,
  type PanInfo,
} from "framer-motion";
import { ChevronLeft, ChevronRight } from "react-iconly";
import { HeroCategoryOrbs } from "@/components/home/hero-category-orbs";
import {
  HERO_DRAG_SETTLE,
  HERO_SHEET_EASE,
  HERO_SHEET_MS,
  HERO_SHEET_MS_MOBILE,
  HERO_SHEET_MS_REDUCED,
  HERO_SHEET_UNDERLAY,
  HERO_SWIPE_CONFIDENCE,
  HERO_SWIPE_OFFSET,
  heroSheetReducedVariants,
  heroSheetTransition,
  heroSheetVariants,
  heroSwipePower,
} from "@/components/home/hero-sheet-motion";
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
/** Hard cap — published pack + dock are designed around 6 slides / 5 featured orbs. */
const MAX_ACTIVE_SLIDES = 6;

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
        "absolute inset-0",
        // Desktop only: opacity/transform transition for menu blur. Mobile strip
        // drag is GPU x-transform — CSS transform transitions fight the finger.
        !lite && "transition-[opacity,transform] duration-300 ease-out will-change-transform",
        blurred && "scale-[1.015] opacity-40",
      )}
      style={{ backgroundColor: HERO_SHEET_UNDERLAY }}
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
          fallback={<div className="absolute inset-0" style={{ backgroundColor: HERO_SHEET_UNDERLAY }} />}
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
                  "flex gap-2 pb-1",
                  config.carousel.layoutPreset === "stack"
                    ? "flex-col"
                    : "h-scroll",
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

/**
 * Sheet strip: next | current | prev (RTL page-turn), drag follows pointer, then settle.
 * Next = content moves right (ورق از چپ به راست).
 * Mobile-only; desktop uses AnimatePresence sheet (arrows + autoplay, no drag).
 *
 * Android smoothness: 1:1 x tracking (±width, tiny elastic) + direction lock.
 * Do NOT setState on drag start — that re-renders 3 SlideCanvases mid-gesture.
 */
function HeroSheetStrip({
  slides,
  index,
  menuOpen,
  packPreset,
  isMobile,
  nudge,
  onNudgeHandled,
  onCommitNext,
  onCommitPrev,
}: {
  slides: DesignedHeroSlide[];
  index: number;
  menuOpen: boolean;
  packPreset: MobileComposePreset;
  isMobile: boolean;
  nudge: "next" | "prev" | null;
  onNudgeHandled: () => void;
  onCommitNext: () => void;
  onCommitPrev: () => void;
}) {
  const count = slides.length;
  const containerRef = useRef<HTMLDivElement>(null);
  const trackRef = useRef<HTMLDivElement>(null);
  const widthRef = useRef(0);
  const [width, setWidth] = useState(0);
  const [locked, setLocked] = useState(false);
  const x = useMotionValue(0);

  const current = slides[index]!;
  const prev = slides[(index - 1 + count) % count]!;
  const next = slides[(index + 1) % count]!;
  const currentPreset = (current.mobilePreset ?? packPreset) as MobileComposePreset;
  const prevPreset = (prev.mobilePreset ?? packPreset) as MobileComposePreset;
  const nextPreset = (next.mobilePreset ?? packPreset) as MobileComposePreset;
  const settleMs = isMobile ? HERO_SHEET_MS_MOBILE : HERO_SHEET_MS;

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const measure = () => {
      const w = el.clientWidth;
      widthRef.current = w;
      setWidth(w);
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const settleTo = useCallback(
    (target: number, commit: () => void) => {
      const w = widthRef.current;
      if (!w) {
        commit();
        x.set(0);
        setLocked(false);
        return;
      }
      setLocked(true);
      animate(x, target, {
        duration: settleMs,
        ease: HERO_SHEET_EASE,
        onComplete: () => {
          // Index + x reset must paint together — otherwise x→0 with stale
          // panels flashes the previous slide (reads as a white/empty gap).
          flushSync(() => {
            commit();
          });
          x.set(0);
          setLocked(false);
        },
      });
    },
    [x, settleMs],
  );

  useEffect(() => {
    if (!nudge || locked) return;
    const w = widthRef.current;
    // RTL next: drag/nudge content to the right (reveals next parked on the left).
    if (nudge === "next") {
      settleTo(w || 1, () => {
        onCommitNext();
        onNudgeHandled();
      });
    } else {
      settleTo(-(w || 1), () => {
        onCommitPrev();
        onNudgeHandled();
      });
    }
  }, [nudge, locked, settleTo, onCommitNext, onCommitPrev, onNudgeHandled]);

  const onDragEnd = useCallback(
    (_: MouseEvent | TouchEvent | PointerEvent, info: PanInfo) => {
      const track = trackRef.current;
      if (track) track.style.touchAction = "pan-y";
      if (menuOpen || locked || count <= 1) {
        animate(x, 0, HERO_DRAG_SETTLE);
        return;
      }
      const w = widthRef.current || 1;
      const { offset, velocity } = info;
      const power = heroSwipePower(offset.x, velocity.x);
      // Drag right → next; drag left → prev (RTL page-turn).
      if (offset.x > HERO_SWIPE_OFFSET || power > HERO_SWIPE_CONFIDENCE) {
        settleTo(w, onCommitNext);
      } else if (offset.x < -HERO_SWIPE_OFFSET || power < -HERO_SWIPE_CONFIDENCE) {
        settleTo(-w, onCommitPrev);
      } else {
        animate(x, 0, HERO_DRAG_SETTLE);
      }
    },
    [menuOpen, locked, count, x, settleTo, onCommitNext, onCommitPrev],
  );

  return (
    <div
      ref={containerRef}
      className="absolute inset-0 overflow-hidden"
      style={{ backgroundColor: HERO_SHEET_UNDERLAY }}
    >
      <motion.div
        ref={trackRef}
        className="absolute inset-0 cursor-grab active:cursor-grabbing"
        style={{
          x,
          willChange: "transform",
          touchAction: "pan-y",
          backgroundColor: HERO_SHEET_UNDERLAY,
        }}
        drag={menuOpen || locked || width <= 0 ? false : "x"}
        dragDirectionLock
        dragConstraints={
          width > 0 ? { left: -width, right: width } : { left: 0, right: 0 }
        }
        dragElastic={0.06}
        dragMomentum={false}
        onDirectionLock={(axis) => {
          // Once horizontal intent is clear, stop Android Chrome from claiming
          // the gesture for vertical scroll (reads as jump / hitch).
          const track = trackRef.current;
          if (track) track.style.touchAction = axis === "x" ? "none" : "pan-y";
        }}
        onDragEnd={onDragEnd}
      >
        {width > 0 ? (
          <>
            <div
              className="absolute inset-0"
              style={{ transform: `translate3d(${-width}px,0,0)` }}
              aria-hidden
            >
              <SlideCanvas
                slide={next}
                reducedMotion={isMobile}
                blurred={menuOpen}
                mobilePreset={nextPreset}
                isMobile={isMobile}
              />
            </div>
            <div className="absolute inset-0">
              <SlideCanvas
                slide={current}
                reducedMotion={isMobile}
                blurred={menuOpen}
                mobilePreset={currentPreset}
                isMobile={isMobile}
                priority={index === 0}
              />
            </div>
            <div
              className="absolute inset-0"
              style={{ transform: `translate3d(${width}px,0,0)` }}
              aria-hidden
            >
              <SlideCanvas
                slide={prev}
                reducedMotion={isMobile}
                blurred={menuOpen}
                mobilePreset={prevPreset}
                isMobile={isMobile}
              />
            </div>
          </>
        ) : (
          <SlideCanvas
            slide={current}
            reducedMotion={isMobile}
            blurred={menuOpen}
            mobilePreset={currentPreset}
            isMobile={isMobile}
            priority={index === 0}
          />
        )}
      </motion.div>
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
  const [sheetNudge, setSheetNudge] = useState<"next" | "prev" | null>(null);
  /** Fine-pointer split: visual left/right half of hero shows only that arrow. */
  const [arrowSide, setArrowSide] = useState<"left" | "right" | null>(null);
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

  const packMobilePreset = (pack.mobilePreset ?? "balanced") as MobileComposePreset;

  const commitNext = useCallback(() => {
    if (!slideCount) return;
    setDirection(1);
    setIndex((i) => (i + 1) % slideCount);
  }, [slideCount]);

  const commitPrev = useCallback(() => {
    if (!slideCount) return;
    setDirection(-1);
    setIndex((i) => (i - 1 + slideCount) % slideCount);
  }, [slideCount]);

  const goNext = useCallback(() => {
    if (!slideCount) return;
    // Mobile strip: nudge-driven settle; desktop AnimatePresence: commit index.
    if (isMobile && !reducedMotion) {
      setSheetNudge((n) => n ?? "next");
      return;
    }
    commitNext();
  }, [slideCount, isMobile, reducedMotion, commitNext]);

  const goPrev = useCallback(() => {
    if (!slideCount) return;
    if (isMobile && !reducedMotion) {
      setSheetNudge((n) => n ?? "prev");
      return;
    }
    commitPrev();
  }, [slideCount, isMobile, reducedMotion, commitPrev]);

  // Desktop-only autoplay — mobile stays swipe/manual (saves timers + slide churn).
  useEffect(() => {
    if (isMobile || slideCount <= 1 || paused || reducedMotion || menuOpen) return;
    const t = window.setInterval(() => {
      commitNext();
    }, AUTOPLAY_MS);
    return () => window.clearInterval(t);
  }, [isMobile, slideCount, paused, reducedMotion, menuOpen, commitNext]);

  if (!slide) return null;

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
      "pointer-events-auto absolute top-1/2 z-30 grid h-12 w-12 -translate-y-1/2 place-items-center rounded-full outline-none",
      "bg-black/68 text-white shadow-[0_10px_28px_rgba(0,0,0,0.44)] ring-1 ring-primary",
      !isMobile && "backdrop-blur-md",
      "transition-[opacity,background-color,box-shadow] duration-300 ease-out",
      "hover-fine:bg-black/78 hover-fine:shadow-[0_12px_32px_rgba(0,0,0,0.5)] hover-fine:ring-primary/80",
      "active:bg-black/82",
      "focus-visible:!opacity-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary",
      // Touch / coarse: always slightly visible (bolder than prior wash)
      "opacity-75",
      // Fine pointer: hidden unless this visual half is hovered (or focused)
      "[@media(hover:hover)_and_(pointer:fine)]:opacity-0",
      arrowSide === side && "[@media(hover:hover)_and_(pointer:fine)]:!opacity-100",
    );

  const sheetDuration = reducedMotion ? HERO_SHEET_MS_REDUCED : HERO_SHEET_MS;
  const sheetVariants = reducedMotion ? heroSheetReducedVariants : heroSheetVariants;
  const useSheetStrip = isMobile && !reducedMotion && slideCount > 1;

  return (
    <section
      ref={regionRef}
      tabIndex={0}
      aria-roledescription="carousel"
      aria-label="هیرو کارزار"
      className="group/hero relative h-[62svh] w-full max-w-full overflow-x-clip outline-none md:h-[100svh]"
      style={{ backgroundColor: HERO_SHEET_UNDERLAY }}
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
    >
      <div
        className="relative h-full w-full overflow-hidden"
        style={{ backgroundColor: HERO_SHEET_UNDERLAY }}
      >
        {useSheetStrip ? (
          <HeroSheetStrip
            slides={slides}
            index={activeIndex}
            menuOpen={menuOpen}
            packPreset={packMobilePreset}
            isMobile={isMobile}
            nudge={sheetNudge}
            onNudgeHandled={() => setSheetNudge(null)}
            onCommitNext={commitNext}
            onCommitPrev={commitPrev}
          />
        ) : (
          <AnimatePresence initial={false} custom={direction} mode="sync">
            <motion.div
              key={slide.id}
              custom={direction}
              variants={sheetVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={heroSheetTransition(sheetDuration)}
              className="absolute inset-0"
              style={{
                willChange: reducedMotion ? undefined : "transform",
                backgroundColor: HERO_SHEET_UNDERLAY,
              }}
            >
              <SlideCanvas
                slide={slide}
                reducedMotion={reducedMotion || isMobile}
                blurred={menuOpen}
                mobilePreset={mobilePreset}
                isMobile={isMobile}
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
              <ChevronLeft set="bold" size={36} />
            </button>
            <button
              type="button"
              aria-label="اسلاید قبلی"
              onClick={goPrev}
              className={cn(slideArrowClass("right"), "right-3 sm:right-5")}
            >
              <ChevronRight set="bold" size={36} />
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
