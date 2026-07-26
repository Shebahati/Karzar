"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import Image from "next/image";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, ChevronLeft, ChevronRight } from "react-iconly";
import { Button } from "@/components/ui/button";
import { Container } from "@/components/ui/container";
import { Skeleton } from "@/components/ui/skeleton";
import { buildHeroSlidesFromNavGroups } from "@/config/hero-from-nav";
import { NAV_GROUPS } from "@/config/nav-groups";
import {
  useCategoryTree,
  useHeroSlides,
  useNavGroupDefs,
} from "@/features/catalog/queries";
import { cn } from "@/lib/utils";

const AUTOPLAY_MS = 5000;
const SWIPE_THRESHOLD = 48;

export function Hero() {
  const cmsQuery = useHeroSlides();
  const treeQuery = useCategoryTree();
  const { data: navDefs = NAV_GROUPS } = useNavGroupDefs();
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const touchStartX = useRef<number | null>(null);
  const regionRef = useRef<HTMLElement>(null);

  const slides = useMemo(
    () =>
      buildHeroSlidesFromNavGroups(
        treeQuery.data ?? [],
        navDefs,
        cmsQuery.data ?? [],
      ),
    [treeQuery.data, navDefs, cmsQuery.data],
  );

  const isLoading = cmsQuery.isLoading || treeQuery.isLoading;

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReducedMotion(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);

  const activeIndex = slides.length ? ((index % slides.length) + slides.length) % slides.length : 0;

  const go = useCallback(
    (next: number) => {
      if (!slides.length) return;
      setIndex(((next % slides.length) + slides.length) % slides.length);
    },
    [slides.length],
  );

  const goNext = useCallback(() => go(activeIndex + 1), [go, activeIndex]);
  const goPrev = useCallback(() => go(activeIndex - 1), [go, activeIndex]);

  useEffect(() => {
    if (slides.length <= 1 || paused || reducedMotion) return;
    const t = window.setInterval(() => {
      setIndex((i) => (i + 1) % slides.length);
    }, AUTOPLAY_MS);
    return () => window.clearInterval(t);
  }, [slides.length, paused, reducedMotion]);

  useEffect(() => {
    const el = regionRef.current;
    if (!el) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        // RTL: left arrow advances to next slide
        goNext();
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        goPrev();
      } else if (e.key === "Home") {
        e.preventDefault();
        go(0);
      } else if (e.key === "End") {
        e.preventDefault();
        go(slides.length - 1);
      }
    };
    el.addEventListener("keydown", onKey);
    return () => el.removeEventListener("keydown", onKey);
  }, [go, goNext, goPrev, slides.length]);

  if (isLoading) {
    return (
      <div className="relative min-h-[min(78vh,560px)] w-full overflow-hidden bg-secondary sm:min-h-[min(72vh,620px)]">
        <Skeleton className="absolute inset-0 rounded-none" />
      </div>
    );
  }

  if (!slides.length) return null;

  const slide = slides[activeIndex];

  return (
    <section
      ref={regionRef}
      tabIndex={0}
      aria-roledescription="carousel"
      aria-label="معرفی دسته‌های اصلی کارزار"
      className="relative outline-none"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
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
        if (start == null) return;
        const dx = (e.changedTouches[0]?.clientX ?? start) - start;
        if (Math.abs(dx) < SWIPE_THRESHOLD) return;
        // RTL swipe: finger moves left (negative dx) → previous in visual order;
        // finger moves right → next. Match common RTL carousel expectation.
        if (dx > 0) goNext();
        else goPrev();
      }}
    >
      <div className="relative min-h-[min(78vh,560px)] w-full overflow-hidden sm:min-h-[min(72vh,620px)]">
        <AnimatePresence mode="wait">
          <motion.div
            key={slide.id}
            initial={{ opacity: 0, scale: reducedMotion ? 1 : 1.04 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: reducedMotion ? 0.15 : 0.55, ease: "easeOut" }}
            className="absolute inset-0"
          >
            <Image
              src={slide.image}
              alt=""
              fill
              priority={activeIndex === 0}
              quality={90}
              sizes="100vw"
              className="object-cover object-[center_40%]"
            />
            <div
              aria-hidden
              className="absolute inset-0 bg-[linear-gradient(180deg,rgba(18,18,18,0.55)_0%,rgba(18,18,18,0.28)_42%,rgba(18,18,18,0.72)_100%)] sm:bg-[linear-gradient(270deg,rgba(18,18,18,0.18)_0%,rgba(18,18,18,0.42)_48%,rgba(18,18,18,0.82)_100%)]"
            />
            <div
              aria-hidden
              className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_20%_0%,rgba(194,32,38,0.22),transparent_42%)]"
            />
          </motion.div>
        </AnimatePresence>

        <Container className="relative z-10 flex min-h-[min(78vh,560px)] flex-col justify-end pb-10 pt-16 sm:min-h-[min(72vh,620px)] sm:justify-center sm:pb-16 sm:pt-20">
          <div className="max-w-xl">
            <p className="text-sm font-bold tracking-wide text-white/90 sm:text-base">
              کارزار
            </p>
            <div
              className="mt-2 h-1 w-12 rounded-full bg-primary sm:mt-3 sm:w-14"
              aria-hidden
            />
            <h1 className="mt-4 text-[1.65rem] font-bold leading-snug text-white sm:mt-5 sm:text-4xl lg:text-[2.75rem] lg:leading-tight">
              {slide.title}
            </h1>
            <p className="mt-3 max-w-lg text-sm leading-7 text-white/88 sm:mt-4 sm:text-base sm:leading-8">
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
                  className="w-full border border-white/30 bg-white/10 text-white hover:bg-white/20 sm:w-auto"
                >
                  مشاهده فروشگاه
                </Button>
              </Link>
            </div>
          </div>

          {slides.length > 1 && (
            <div className="mt-8 flex items-center justify-between gap-4 sm:mt-12">
              <div className="flex gap-1.5" role="tablist" aria-label="انتخاب اسلاید">
                {slides.map((s, i) => (
                  <button
                    key={s.id}
                    type="button"
                    role="tab"
                    aria-label={`${s.title} — اسلاید ${i + 1}`}
                    aria-selected={i === activeIndex}
                    onClick={() => setIndex(i)}
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

              <div className="flex gap-2">
                <button
                  type="button"
                  aria-label="اسلاید بعدی"
                  onClick={goNext}
                  className="grid h-10 w-10 place-items-center rounded-full border border-white/30 bg-black/25 text-white backdrop-blur-sm transition hover:bg-black/40"
                >
                  <ChevronRight set="light" size="small" />
                </button>
                <button
                  type="button"
                  aria-label="اسلاید قبلی"
                  onClick={goPrev}
                  className="grid h-10 w-10 place-items-center rounded-full border border-white/30 bg-black/25 text-white backdrop-blur-sm transition hover:bg-black/40"
                >
                  <ChevronLeft set="light" size="small" />
                </button>
              </div>
            </div>
          )}
        </Container>

        <span className="sr-only" aria-live="polite">
          {slide.title}
        </span>
      </div>
    </section>
  );
}
