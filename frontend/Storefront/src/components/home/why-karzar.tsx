"use client";

import { useEffect, useRef, useState } from "react";
import { motion, useInView } from "framer-motion";
import { Chart, Send, ShieldDone, TwoUsers } from "react-iconly";
import { cn } from "@/lib/utils";
import { useMotionSafe } from "@/lib/use-motion-safe";

const SERVICES = [
  {
    Icon: ShieldDone,
    title: "ضمانت اصالت کالا",
    desc: "تمام محصولات مستقیماً از نمایندگی‌های رسمی عرضه می‌شوند.",
    tone: "steel" as const,
  },
  {
    Icon: Chart,
    title: "قیمت‌گذاری B2B",
    desc: "تخفیف پلکانی برای خریدهای سازمانی با فاکتور رسمی.",
    tone: "primary" as const,
  },
  {
    Icon: Send,
    title: "ارسال سریع",
    desc: "بسته‌بندی استاندارد و ارسال مطمئن به سراسر کشور.",
    tone: "steel" as const,
  },
  {
    Icon: TwoUsers,
    title: "مشاوره تخصصی",
    desc: "انتخاب درست ابزار متناسب با نیاز شما.",
    tone: "steel" as const,
  },
];

/**
 * Desktop: scroll-locks briefly while cards rise one-by-one.
 * Mobile: softer staggered reveal without hard lock.
 */
export function WhyKarzar() {
  const sectionRef = useRef<HTMLElement>(null);
  const inView = useInView(sectionRef, { amount: 0.45, once: false });
  const motionSafe = useMotionSafe();
  const [active, setActive] = useState(0);
  const [played, setPlayed] = useState(false);
  const locking = useRef(false);

  useEffect(() => {
    if (!inView || played || !motionSafe) return;
    if (typeof window === "undefined") return;
    if (window.matchMedia("(max-width: 1023px)").matches) {
      setPlayed(true);
      setActive(SERVICES.length);
      return;
    }

    if (locking.current) return;
    locking.current = true;
    const startY = window.scrollY;
    let step = 0;

    const prevOverflow = document.documentElement.style.overflow;
    document.documentElement.style.overflow = "hidden";

    const tick = window.setInterval(() => {
      step += 1;
      setActive(step);
      if (step >= SERVICES.length) {
        window.clearInterval(tick);
        document.documentElement.style.overflow = prevOverflow;
        setPlayed(true);
        locking.current = false;
        window.scrollTo({ top: startY, behavior: "instant" as ScrollBehavior });
      }
    }, 520);

    return () => {
      window.clearInterval(tick);
      document.documentElement.style.overflow = prevOverflow;
      locking.current = false;
    };
  }, [inView, played, motionSafe]);

  useEffect(() => {
    if (!motionSafe) {
      setActive(SERVICES.length);
      setPlayed(true);
    }
  }, [motionSafe]);

  return (
    <section
      ref={sectionRef}
      className="relative overflow-hidden rounded-[1.75rem] border border-border/50 bg-gradient-to-br from-card via-card to-secondary/80 px-5 py-10 sm:px-10 sm:py-14"
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(94,95,94,0.08),_transparent_55%)]" />

      <div className="relative mb-10 max-w-xl text-center lg:mx-auto lg:mb-14">
        <span className="inline-block rounded-full border border-steel/15 bg-secondary px-3 py-1 text-xs font-bold text-steel">
          چرا کارزار؟
        </span>
        <h2 className="mt-4 text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
          تجربه حرفه‌ای خرید ابزار صنعتی
        </h2>
        <p className="mx-auto mt-2 text-sm leading-7 text-steel">
          خدماتی که خرید شما را مطمئن، سریع و به‌صرفه می‌کند
        </p>
      </div>

      <div className="relative mx-auto grid max-w-5xl gap-4 sm:grid-cols-2">
        {SERVICES.map(({ Icon, title, desc, tone }, index) => {
          const visible = active > index;
          return (
            <motion.article
              key={title}
              initial={false}
              animate={
                visible
                  ? { opacity: 1, y: 0, scale: 1 }
                  : { opacity: 0, y: 64, scale: 0.96 }
              }
              transition={{ type: "spring", stiffness: 120, damping: 18 }}
              className={cn(
                "rounded-2xl border border-border/40 bg-card/95 p-5 shadow-soft backdrop-blur-sm sm:p-6",
                visible && "shadow-glass",
              )}
            >
              <span
                className={cn(
                  "grid h-12 w-12 place-items-center rounded-xl",
                  tone === "primary"
                    ? "bg-primary text-primary-foreground"
                    : "bg-steel text-steel-foreground",
                )}
              >
                <Icon set="bold" />
              </span>
              <h3 className="mt-4 text-base font-bold text-foreground sm:text-lg">{title}</h3>
              <p className="mt-2 text-sm leading-7 text-steel">{desc}</p>
            </motion.article>
          );
        })}
      </div>
    </section>
  );
}
