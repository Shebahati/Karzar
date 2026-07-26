"use client";

import { motion } from "framer-motion";
import { Chart, Send, ShieldDone, TwoUsers } from "react-iconly";
import { cn } from "@/lib/utils";
import { useMotionSafe } from "@/lib/use-motion-safe";

const SERVICES = [
  {
    Icon: ShieldDone,
    title: "ضمانت اصالت کالا",
    desc: "تمام محصولات مستقیماً از نمایندگی‌های رسمی عرضه می‌شوند.",
    tone: "primary" as const,
  },
  {
    Icon: Chart,
    title: "قیمت‌گذاری B2B",
    desc: "تخفیف پلکانی برای خریدهای سازمانی با فاکتور رسمی.",
    tone: "steel" as const,
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
    desc: "انتخاب درست ابزار متناسب با نیاز خط تولید شما.",
    tone: "steel" as const,
  },
];

/**
 * Trust section — one composition, brand-forward, intentional stagger.
 * No scroll-lock; respects reduced-motion.
 */
export function WhyKarzar() {
  const motionSafe = useMotionSafe();

  return (
    <section
      aria-labelledby="why-karzar-heading"
      className="relative overflow-hidden rounded-[1.75rem] border border-border/45 bg-[#1a1c1b] px-5 py-12 text-white sm:px-10 sm:py-16"
    >
      {/* Atmosphere — steel grain + red accent wash (not purple) */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_120%_80%_at_100%_0%,rgba(194,32,38,0.22),transparent_55%),radial-gradient(ellipse_90%_70%_at_0%_100%,rgba(94,95,94,0.35),transparent_50%)]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.07]"
        style={{
          backgroundImage:
            "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")",
        }}
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -start-24 top-1/2 h-64 w-64 -translate-y-1/2 rounded-full bg-primary/20 blur-3xl"
      />

      <div className="relative mx-auto max-w-3xl text-center">
        <motion.p
          initial={motionSafe ? { opacity: 0, y: 12 } : false}
          whileInView={motionSafe ? { opacity: 1, y: 0 } : undefined}
          viewport={{ once: true, amount: 0.6 }}
          transition={{ duration: 0.45 }}
          className="text-[11px] font-bold tracking-[0.22em] text-primary"
        >
          چرا کارزار
        </motion.p>
        <motion.h2
          id="why-karzar-heading"
          initial={motionSafe ? { opacity: 0, y: 16 } : false}
          whileInView={motionSafe ? { opacity: 1, y: 0 } : undefined}
          viewport={{ once: true, amount: 0.6 }}
          transition={{ duration: 0.5, delay: 0.06 }}
          className="mt-3 text-3xl font-bold tracking-tight text-white sm:text-4xl"
        >
          خرید ابزار صنعتی با اطمینان کارگاهی
        </motion.h2>
        <motion.p
          initial={motionSafe ? { opacity: 0, y: 14 } : false}
          whileInView={motionSafe ? { opacity: 1, y: 0 } : undefined}
          viewport={{ once: true, amount: 0.6 }}
          transition={{ duration: 0.5, delay: 0.12 }}
          className="mx-auto mt-3 max-w-xl text-sm leading-7 text-white/65 sm:text-base"
        >
          اصالت، قیمت سازمانی، ارسال مطمئن و مشاوره تخصصی — مسیر خرید برای خط تولید شما.
        </motion.p>
      </div>

      <div className="relative mx-auto mt-12 grid max-w-5xl gap-px overflow-hidden rounded-2xl border border-white/10 bg-white/10 sm:grid-cols-2">
        {SERVICES.map(({ Icon, title, desc, tone }, index) => (
          <motion.article
            key={title}
            initial={motionSafe ? { opacity: 0, y: 28 } : false}
            whileInView={motionSafe ? { opacity: 1, y: 0 } : undefined}
            viewport={{ once: true, amount: 0.35 }}
            transition={{ duration: 0.45, delay: Math.min(0.08 * index, 0.28) }}
            className="group relative bg-[#222524]/95 p-6 backdrop-blur-sm sm:p-8"
          >
            <span
              className={cn(
                "grid h-12 w-12 place-items-center rounded-xl transition-transform duration-500 group-hover:scale-105",
                tone === "primary"
                  ? "bg-primary text-white"
                  : "bg-white/10 text-white ring-1 ring-white/15",
              )}
            >
              <Icon set="bold" />
            </span>
            <h3 className="mt-5 text-lg font-bold text-white">{title}</h3>
            <p className="mt-2 max-w-sm text-sm leading-7 text-white/60">{desc}</p>
            <span
              aria-hidden
              className="pointer-events-none absolute inset-x-0 bottom-0 h-px origin-end scale-x-0 bg-gradient-to-l from-primary/80 to-transparent transition-transform duration-500 group-hover:scale-x-100"
            />
          </motion.article>
        ))}
      </div>
    </section>
  );
}
