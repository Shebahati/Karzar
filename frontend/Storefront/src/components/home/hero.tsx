"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, ChevronLeft, ChevronRight } from "react-iconly";
import { Button } from "@/components/ui/button";
import { SafeImage } from "@/components/ui/safe-image";
import { Skeleton } from "@/components/ui/skeleton";
import { HeroCategoryOrbs } from "@/components/home/hero-category-orbs";
import { DesignedHero } from "@/components/home/designed-hero";
import {
  featuredOrbs,
  matchOrbToTreeNode,
  orbHref,
  orbsFromRoots,
} from "@/config/hero-orbs";
import { orderedTaxonomyRoots, NAV_GROUPS } from "@/config/nav-groups";
import { useCategoryTree, useHeroSlides, useNavGroupDefs } from "@/features/catalog/queries";
import { useDesignedHeroPack } from "@/features/home/use-hero-design";
import { lcpImageProps } from "@/lib/cwv";
import { cn } from "@/lib/utils";
import type { HeroSlide } from "@/types/content";
import type { CategoryTreeNode } from "@/types/category";

const AUTOPLAY_MS = 5500;
const SWIPE_THRESHOLD = 48;
const easePremium = [0.22, 1, 0.36, 1] as const;

const copyShadow =
  "0 1px 2px rgba(0,0,0,0.72), 0 2px 16px rgba(0,0,0,0.45)";

function buildOrbSlides(
  roots: CategoryTreeNode[],
  cms: HeroSlide[],
): HeroSlide[] {
  const orbs = orbsFromRoots(roots);
  const featured = featuredOrbs(orbs.length ? orbs : undefined);
  const usedCms = new Set<number>();

  return featured.map((orb, index) => {
    const node = matchOrbToTreeNode(orb, roots);
    const cmsMatch = cms.find((s) => {
      if (usedCms.has(s.id)) return false;
      const t = (s.title ?? "").replace(/\u200c/g, "");
      return t.includes(orb.name.slice(0, 6)) || orb.name.includes(t.slice(0, 6));
    });
    if (cmsMatch) usedCms.add(cmsMatch.id);

    return {
      id: cmsMatch?.id ?? index + 1,
      title: cmsMatch?.title?.trim() || orb.name,
      subtitle: cmsMatch?.subtitle?.trim() || orb.subtitle,
      cta_label: (cmsMatch?.cta_label?.trim() || orb.ctaLabel).replace(/\s*←\s*$/u, ""),
      cta_href: cmsMatch?.cta_href?.trim() || orbHref(orb, node),
      image: cmsMatch?.image?.trim() || orb.heroImage,
      accent: cmsMatch?.accent?.trim() || "#D02327",
    };
  });
}

export function Hero() {
  const designQuery = useDesignedHeroPack();
  const cmsQuery = useHeroSlides();
  const treeQuery = useCategoryTree();
  const { data: navDefs = NAV_GROUPS } = useNavGroupDefs();
  const [index, setIndex] = useState(0);
  const [direction, setDirection] = useState(1);
  const [paused, setPaused] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  /** Fine-pointer split: visual left/right half of hero shows only that arrow. */
  const [arrowSide, setArrowSide] = useState<"left" | "right" | null>(null);
  const touchStartX = useRef<number | null>(null);
  const regionRef = useRef<HTMLElement>(null);

  const designedPack = designQuery.data;
  const hasDesigned =
    !!designedPack?.slides?.filter((s) => s.isActive).length;

  const roots = useMemo(
    () => orderedTaxonomyRoots(treeQuery.data ?? [], navDefs),
    [treeQuery.data, navDefs],
  );

  const slides = useMemo(
    () => buildOrbSlides(roots, cmsQuery.data ?? []),
    [roots, cmsQuery.data],
  );

  const isLoading =
    designQuery.isLoading ||
    (!hasDesigned && (cmsQuery.isLoading || treeQuery.isLoading));

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
    if (hasDesigned || isMobile || menuOpen || slides.length <= 1 || paused || reducedMotion) {
      return;
    }
    const t = window.setInterval(() => {
      setDirection(1);
      setIndex((i) => (i + 1) % slides.length);
    }, AUTOPLAY_MS);
    return () => window.clearInterval(t);
  }, [hasDesigned, isMobile, menuOpen, slides.length, paused, reducedMotion]);

  useEffect(() => {
    if (hasDesigned) return;
    const el = regionRef.current;
    if (!el) return;
    const onKey = (e: KeyboardEvent) => {
      if (menuOpen) {
        if (e.key === "Escape") {
          e.preventDefault();
          setMenuOpen(false);
        }
        return;
      }
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        goNext();
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        goPrev();
      }
    };
    el.addEventListener("keydown", onKey);
    return () => el.removeEventListener("keydown", onKey);
  }, [hasDesigned, menuOpen, goNext, goPrev]);

  if (isLoading) {
    return (
      <div className="relative h-[62dvh] w-full overflow-hidden bg-secondary md:h-[100dvh]">
        <Skeleton className="absolute inset-0 rounded-none" />
      </div>
    );
  }

  if (hasDesigned && designedPack) {
    return (
      <DesignedHero
        pack={designedPack}
        roots={roots}
        menuOpen={menuOpen}
        onMenuOpenChange={setMenuOpen}
      />
    );
  }

  if (!slides.length) return null;

  const slide = slides[activeIndex]!;
  const liteMotion = isMobile || reducedMotion;
  const slideMs = liteMotion ? 0.12 : 0.85;
  const textX = liteMotion ? 0 : direction * 28;

  const slideArrowClass = (side: "left" | "right") =>
    cn(
      "pointer-events-auto absolute top-1/2 z-30 grid h-11 w-11 -translate-y-1/2 place-items-center rounded-full",
      "bg-black/35 text-white shadow-[0_8px_22px_rgba(0,0,0,0.24)]",
      !isMobile && "backdrop-blur-md",
      "transition-[opacity,background-color,box-shadow] duration-300 ease-out",
      "hover-fine:bg-black/48 hover-fine:shadow-[0_10px_28px_rgba(0,0,0,0.32)]",
      "active:bg-black/55",
      "focus-visible:!opacity-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white/55",
      "opacity-40",
      "[@media(hover:hover)_and_(pointer:fine)]:opacity-0",
      arrowSide === side && "[@media(hover:hover)_and_(pointer:fine)]:!opacity-100",
    );

  return (
    <section
      ref={regionRef}
      tabIndex={0}
      aria-roledescription="carousel"
      aria-label="هیرو دسته‌بندی‌های کارزار"
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
      onFocusCapture={() => setPaused(true)}
      onBlurCapture={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node | null)) {
          setPaused(false);
        }
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
        if (dx > 0) goNext();
        else goPrev();
      }}
    >
      <div className="relative h-full w-full overflow-hidden">
        {liteMotion ? (
          <div
            key={slide.id}
            className={cn(
              "absolute inset-0 transition-opacity duration-200",
              menuOpen && "opacity-40",
            )}
          >
            <SafeImage
              src={slide.image}
              alt=""
              fill
              sizes="100vw"
              className="object-cover object-[left_42%]"
              fallback={<div className="absolute inset-0 bg-[#1a1a1a]" />}
              {...(activeIndex === 0 ? lcpImageProps() : { loading: "lazy" as const })}
            />
            <div
              aria-hidden
              className="absolute inset-0 bg-[linear-gradient(180deg,rgba(18,18,18,0.45)_0%,rgba(18,18,18,0.22)_38%,rgba(18,18,18,0.72)_100%)] sm:bg-[linear-gradient(105deg,rgba(18,18,18,0.12)_0%,rgba(18,18,18,0.35)_48%,rgba(18,18,18,0.82)_78%,rgba(18,18,18,0.92)_100%)]"
            />
            <div
              aria-hidden
              className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_80%_0%,rgba(208,35,39,0.22),transparent_42%)]"
            />
          </div>
        ) : (
          <AnimatePresence initial={false} custom={direction}>
            <motion.div
              key={slide.id}
              custom={direction}
              initial={{ opacity: 0 }}
              animate={{ opacity: menuOpen ? 0.42 : 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: slideMs, ease: easePremium }}
              className={cn(
                "absolute inset-0 transition-transform duration-300 ease-out",
                menuOpen && "scale-[1.015]",
              )}
            >
              <motion.div
                className="absolute inset-0 origin-center will-change-transform"
                initial={{
                  scale: 1.06,
                  x: direction * -18,
                }}
                animate={{
                  scale: 1.1,
                  x: 0,
                }}
                transition={{
                  scale: { duration: AUTOPLAY_MS / 1000, ease: "linear" },
                  x: { duration: slideMs, ease: easePremium },
                }}
              >
                <SafeImage
                  src={slide.image}
                  alt=""
                  fill
                  sizes="100vw"
                  className="object-cover object-[left_42%]"
                  fallback={<div className="absolute inset-0 bg-[#1a1a1a]" />}
                  {...(activeIndex === 0 ? lcpImageProps() : { loading: "lazy" as const })}
                />
              </motion.div>
              <div
                aria-hidden
                className="absolute inset-0 bg-[linear-gradient(180deg,rgba(18,18,18,0.45)_0%,rgba(18,18,18,0.22)_38%,rgba(18,18,18,0.72)_100%)] sm:bg-[linear-gradient(105deg,rgba(18,18,18,0.12)_0%,rgba(18,18,18,0.35)_48%,rgba(18,18,18,0.82)_78%,rgba(18,18,18,0.92)_100%)]"
              />
              <div
                aria-hidden
                className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_80%_0%,rgba(208,35,39,0.22),transparent_42%)]"
              />
            </motion.div>
          </AnimatePresence>
        )}

        <div
          className={cn(
            "relative z-10 flex h-full flex-col justify-center px-5 pb-36 pt-[calc(5.5rem+env(safe-area-inset-top,0px))] transition-[opacity,transform] duration-300 ease-out sm:px-10 lg:px-16",
            menuOpen && "pointer-events-none translate-y-1 opacity-35",
          )}
        >
          <div className="max-w-xl">
            {liteMotion ? (
              <div key={slide.id}>
                <p
                  className="text-sm font-bold tracking-wide text-white sm:text-base"
                  style={{ textShadow: copyShadow }}
                >
                  کارزار
                </p>
                <div className="mt-2 h-1 w-12 rounded-full bg-primary sm:mt-3 sm:w-14" aria-hidden />
                <h1
                  className="mt-4 text-[1.7rem] font-bold leading-snug text-white sm:mt-5 sm:text-4xl lg:text-[2.75rem] lg:leading-tight"
                  style={{ textShadow: copyShadow }}
                >
                  {slide.title}
                </h1>
                <p
                  className="mt-3 max-w-lg text-sm leading-7 text-white/95 sm:mt-4 sm:text-base sm:leading-8"
                  style={{ textShadow: copyShadow }}
                >
                  {slide.subtitle}
                </p>

                <div className="mt-6 flex flex-col gap-2.5 sm:mt-8 sm:flex-row sm:flex-wrap sm:gap-3">
                  <Link href={slide.cta_href} className="w-full sm:w-auto">
                    <Button size="lg" className="w-full gap-2 sm:w-auto">
                      {slide.cta_label}
                      <ArrowLeft set="bold" size="small" />
                    </Button>
                  </Link>
                  <Link href="/catalog" className="w-full sm:w-auto">
                    <Button
                      size="lg"
                      variant="soft"
                      className="w-full border border-white/30 bg-white/10 text-white shadow-none ring-white/20 hover-fine:bg-white/20 hover-fine:text-white hover-fine:shadow-none hover-fine:ring-white/30 hover-fine:translate-y-0 sm:w-auto"
                    >
                      مشاهده فروشگاه
                    </Button>
                  </Link>
                </div>
              </div>
            ) : (
              <AnimatePresence mode="wait" initial={false} custom={direction}>
                <motion.div
                  key={slide.id}
                  custom={direction}
                  initial={{ opacity: 0, x: textX, y: 10 }}
                  animate={{ opacity: 1, x: 0, y: 0 }}
                  exit={{
                    opacity: 0,
                    x: direction * -18,
                    y: -6,
                  }}
                  transition={{ duration: 0.55, ease: easePremium }}
                >
                  <p
                    className="text-sm font-bold tracking-wide text-white sm:text-base"
                    style={{ textShadow: copyShadow }}
                  >
                    کارزار
                  </p>
                  <div className="mt-2 h-1 w-12 rounded-full bg-primary sm:mt-3 sm:w-14" aria-hidden />
                  <h1
                    className="mt-4 text-[1.7rem] font-bold leading-snug text-white sm:mt-5 sm:text-4xl lg:text-[2.75rem] lg:leading-tight"
                    style={{ textShadow: copyShadow }}
                  >
                    {slide.title}
                  </h1>
                  <p
                    className="mt-3 max-w-lg text-sm leading-7 text-white/95 sm:mt-4 sm:text-base sm:leading-8"
                    style={{ textShadow: copyShadow }}
                  >
                    {slide.subtitle}
                  </p>

                  <div className="mt-6 flex flex-col gap-2.5 sm:mt-8 sm:flex-row sm:flex-wrap sm:gap-3">
                    <Link href={slide.cta_href} className="w-full sm:w-auto">
                      <Button size="lg" className="w-full gap-2 sm:w-auto">
                        {slide.cta_label}
                        <ArrowLeft set="bold" size="small" />
                      </Button>
                    </Link>
                    <Link href="/catalog" className="w-full sm:w-auto">
                      <Button
                        size="lg"
                        variant="soft"
                        className="w-full border border-white/30 bg-white/10 text-white shadow-none ring-white/20 hover-fine:bg-white/20 hover-fine:text-white hover-fine:shadow-none hover-fine:ring-white/30 hover-fine:translate-y-0 sm:w-auto"
                      >
                        مشاهده فروشگاه
                      </Button>
                    </Link>
                  </div>
                </motion.div>
              </AnimatePresence>
            )}
          </div>

          {slides.length > 1 && !menuOpen ? (
            <div className="mt-8 flex items-center gap-4 sm:mt-10">
              <div className="flex gap-1.5" role="tablist" aria-label="انتخاب اسلاید">
                {slides.map((s, i) => (
                  <button
                    key={s.id}
                    type="button"
                    role="tab"
                    aria-selected={i === activeIndex}
                    onClick={() => goTo(i)}
                    className="touch-target rounded-full"
                  >
                    <span
                      className={cn(
                        "block h-2 rounded-full transition-all duration-300",
                        i === activeIndex ? "w-8 bg-primary" : "w-2.5 bg-white/50 hover:bg-white/75",
                      )}
                    />
                  </button>
                ))}
              </div>
            </div>
          ) : null}
        </div>

        {slides.length > 1 && !menuOpen ? (
          <>
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
            activeIndex={activeIndex}
            roots={roots}
            defs={orbsFromRoots(roots)}
            menuOpen={menuOpen}
            onMenuOpenChange={setMenuOpen}
          />
        ) : null}

        <span className="sr-only" aria-live="polite">
          {slide.title}
        </span>
      </div>
    </section>
  );
}
