"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Call, Document, Send, ShieldDone } from "react-iconly";
import { cn } from "@/lib/utils";

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
    desc: "پاسخگویی ۹ تا ۱۹",
  },
  {
    Icon: Document,
    title: "پیش‌فاکتور آنی",
    desc: "استعلام و صدور رسمی",
  },
] as const;

/** Light stagger is fine on mobile; only skip when the user prefers reduced motion. */
function usePrefersReducedMotion(): boolean {
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

export function FeatureStrip() {
  const reduceMotion = usePrefersReducedMotion();

  return (
    <section aria-label="مزایای خرید از کارزار">
      <ul className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4 lg:gap-5">
        {FEATURES.map(({ Icon, title, desc }, i) => (
          <motion.li
            key={title}
            initial={reduceMotion ? false : { opacity: 0, y: 28 }}
            whileInView={reduceMotion ? undefined : { opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.35 }}
            transition={
              reduceMotion
                ? undefined
                : {
                    duration: 0.5,
                    delay: i * 0.12,
                    ease: [0.22, 1, 0.36, 1],
                  }
            }
          >
            <article
              className={cn(
                "group relative flex h-full flex-col gap-4 overflow-hidden rounded-2xl",
                "bg-card px-4 py-5 sm:gap-5 sm:px-5 sm:py-6",
                "shadow-[0_1px_0_rgba(94,95,94,0.06),0_12px_28px_-18px_rgba(94,95,94,0.28)]",
                "transition-[transform,box-shadow] duration-400 ease-out",
                "hover:-translate-y-0.5 hover:shadow-[0_1px_0_rgba(94,95,94,0.08),0_18px_36px_-16px_rgba(208,35,39,0.18)]",
              )}
            >
              {/* Soft brand wash — top edge only, no border frame */}
              <span
                aria-hidden
                className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-l from-transparent via-primary/35 to-transparent opacity-70 transition-opacity duration-400 group-hover:opacity-100"
              />
              <span
                aria-hidden
                className="pointer-events-none absolute -end-10 -top-10 h-28 w-28 rounded-full bg-primary/[0.04] transition-transform duration-500 group-hover:scale-110"
              />

              <span
                className={cn(
                  "relative grid h-12 w-12 place-items-center rounded-2xl sm:h-14 sm:w-14",
                  "bg-primary/[0.08] text-primary",
                  "ring-1 ring-inset ring-primary/10",
                  "transition-[background-color,transform] duration-400",
                  "group-hover:bg-primary/[0.12] group-hover:scale-[1.04]",
                )}
              >
                <Icon set="bold" primaryColor="#D02327" />
              </span>

              <div className="relative space-y-1.5">
                <h3 className="text-[15px] font-black tracking-tight text-foreground sm:text-base">
                  {title}
                </h3>
                <p className="text-[12px] font-medium leading-6 text-steel sm:text-[13px] sm:leading-7">
                  {desc}
                </p>
              </div>
            </article>
          </motion.li>
        ))}
      </ul>
    </section>
  );
}
