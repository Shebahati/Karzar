"use client";

import { Call, Document, Send, ShieldDone } from "react-iconly";
import { cn } from "@/lib/utils";
import { useMotionSafe } from "@/lib/use-motion-safe";
import { motion } from "framer-motion";

const FEATURES = [
  {
    Icon: ShieldDone,
    title: "ضمانت اصالت",
    desc: "اصل بودن همه کالاها",
  },
  {
    Icon: Send,
    title: "ارسال سریع",
    desc: "پوشش سراسر کشور",
  },
  {
    Icon: Call,
    title: "پشتیبانی دائم",
    desc: "پاسخگویی ۹ تا ۱۸",
  },
  {
    Icon: Document,
    title: "پیش‌فاکتور آنی",
    desc: "استعلام و صدور رسمی",
  },
] as const;

/** Compact trust strip — dense icon + title + one line, soft surface. */
export function FeatureStrip() {
  const motionSafe = useMotionSafe();

  return (
    <section aria-label="مزایای خرید از کارزار">
      <ul className="grid grid-cols-2 gap-2 sm:gap-2.5 lg:grid-cols-4 lg:gap-3">
        {FEATURES.map(({ Icon, title, desc }, i) => {
          const card = (
            <article
              className={cn(
                "group relative flex h-full items-start gap-3 overflow-hidden rounded-2xl",
                "bg-[#F7F7F7] px-3.5 py-3 sm:px-4 sm:py-3.5",
                "ring-1 ring-inset ring-[#5E5F5E]/[0.08]",
                "shadow-[0_1px_0_rgba(94,95,94,0.04),0_8px_20px_-14px_rgba(94,95,94,0.22)]",
                "transition-[transform,box-shadow,background-color] duration-300 ease-out",
                "hover:-translate-y-0.5 hover:bg-white",
                "hover:shadow-[0_1px_0_rgba(94,95,94,0.06),0_14px_28px_-16px_rgba(208,35,39,0.16)]",
                "hover:ring-primary/15",
              )}
            >
              <span
                aria-hidden
                className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-l from-transparent via-primary/30 to-transparent opacity-60 transition-opacity duration-300 group-hover:opacity-100"
              />

              <span
                className={cn(
                  "relative mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-xl sm:h-10 sm:w-10",
                  "bg-primary/[0.07] text-primary",
                  "ring-1 ring-inset ring-primary/10",
                  "transition-[background-color,transform] duration-300",
                  "group-hover:bg-primary/[0.11] group-hover:scale-[1.03]",
                )}
              >
                <Icon set="bold" primaryColor="#D02327" size="small" />
              </span>

              <div className="relative min-w-0 space-y-0.5 pt-0.5">
                <h3 className="text-[13px] font-black leading-snug tracking-tight text-foreground sm:text-[14px]">
                  {title}
                </h3>
                <p className="text-[11px] font-medium leading-5 text-[#5E5F5E] sm:text-[12px] sm:leading-5">
                  {desc}
                </p>
              </div>
            </article>
          );

          // Desktop only: entrance stagger. Mobile / reduced-motion: static list.
          if (!motionSafe) {
            return <li key={title}>{card}</li>;
          }

          return (
            <motion.li
              key={title}
              initial={{ opacity: 0, y: 14 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.4 }}
              transition={{
                duration: 0.4,
                delay: i * 0.07,
                ease: [0.22, 1, 0.36, 1],
              }}
            >
              {card}
            </motion.li>
          );
        })}
      </ul>
    </section>
  );
}
