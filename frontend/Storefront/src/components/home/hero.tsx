"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft } from "react-iconly";
import { Button } from "@/components/ui/button";
import { useHeroSlides } from "@/features/catalog/queries";
import { useMotionSafe } from "@/lib/use-motion-safe";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export function Hero() {
  const { data, isLoading } = useHeroSlides();
  const [index, setIndex] = useState(0);
  const motionSafe = useMotionSafe();
  const slides = data ?? [];

  useEffect(() => {
    if (slides.length <= 1) return;
    const t = setInterval(() => setIndex((i) => (i + 1) % slides.length), 7000);
    return () => clearInterval(t);
  }, [slides.length]);

  if (isLoading) {
    return <Skeleton className="h-[320px] w-full rounded-2xl sm:h-[420px] sm:rounded-3xl" />;
  }
  if (!slides.length) return null;

  const slide = slides[index];

  return (
    <div className="relative overflow-hidden rounded-2xl border border-border/50 bg-card shadow-elevated sm:rounded-[1.75rem]">
      <div className="relative min-h-[320px] sm:min-h-[420px]">
        <AnimatePresence mode="wait">
          <motion.div
            key={slide.id}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: motionSafe ? 0.5 : 0.2 }}
            className="absolute inset-0"
          >
            <Image
              src={slide.image}
              alt={slide.title}
              fill
              priority
              sizes="100vw"
              className="object-cover object-[20%_45%]"
            />
            <div
              aria-hidden
              className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/35 to-transparent sm:bg-gradient-to-l sm:from-black/80 sm:via-black/30 sm:to-transparent"
            />
            <div
              aria-hidden
              className="pointer-events-none absolute inset-x-0 bottom-0 h-[72%] bg-gradient-to-t from-black/70 via-black/25 to-transparent sm:inset-y-0 sm:start-0 sm:end-auto sm:h-full sm:w-[55%] sm:bg-gradient-to-l sm:from-black/65 sm:via-black/20 sm:to-transparent"
            />
          </motion.div>
        </AnimatePresence>

        <div className="relative z-10 flex min-h-[320px] flex-col justify-end gap-4 p-5 pb-5 sm:min-h-[420px] sm:justify-center sm:gap-0 sm:p-12">
          {slides.length > 1 && (
            <div className="mb-1 flex gap-1 sm:absolute sm:bottom-8 sm:start-12 sm:mb-0 sm:z-10">
              {slides.map((s, i) => (
                <button
                  key={s.id}
                  type="button"
                  aria-label={`اسلاید ${i + 1}`}
                  aria-current={i === index}
                  onClick={() => setIndex(i)}
                  className="touch-target rounded-full"
                >
                  <span
                    className={cn(
                      "block h-2 rounded-full transition-all",
                      i === index ? "w-8 bg-primary" : "w-2.5 bg-white/55",
                    )}
                  />
                </button>
              ))}
            </div>
          )}

          <div className="sm:max-w-[min(100%,36rem)]">
            <h1 className="max-w-xl text-[1.35rem] font-bold leading-snug text-white sm:text-4xl lg:text-[2.65rem] lg:leading-tight">
              {slide.title}
            </h1>
            <p className="mt-2 max-w-lg text-sm leading-6 text-white/90 sm:mt-3 sm:text-base sm:leading-7">
              {slide.subtitle}
            </p>
          </div>

          <div className="flex flex-col gap-2.5 sm:mt-8 sm:max-w-[min(100%,36rem)] sm:flex-row sm:flex-wrap sm:gap-3">
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
                className="w-full border border-white/25 bg-white/10 text-white hover:bg-white/20 sm:w-auto"
              >
                مشاهده فروشگاه
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
