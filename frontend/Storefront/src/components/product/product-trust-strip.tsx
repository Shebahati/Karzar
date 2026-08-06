"use client";

import { Call, Document, Send, ShieldDone, Swap, Wallet } from "react-iconly";
import { cn } from "@/lib/utils";

export type PdpTrustItem = {
  key: string;
  title: string;
  desc: string;
  Icon: typeof ShieldDone;
};

/**
 * Trust cues for the sticky buy card (authenticity / warranty / return).
 * Does not invent certifications — product warranty is optional SoT copy only.
 * Shipping / support / payment live on PdpAssistStrip below the hero.
 */
export function buildPdpTrustItems(opts: {
  warrantyText?: string | null;
  isOriginal?: boolean;
}): PdpTrustItem[] {
  const items: PdpTrustItem[] = [
    {
      key: "authenticity",
      title: "ضمانت اصالت",
      desc: opts.isOriginal ? "کالای اصلی" : "نمایندگی رسمی",
      Icon: ShieldDone,
    },
  ];

  if (opts.warrantyText?.trim()) {
    items.push({
      key: "warranty",
      title: opts.warrantyText.trim(),
      desc: "شرایط گارانتی",
      Icon: Document,
    });
  }

  items.push({
    key: "return",
    title: "۷ روز بازگشت",
    desc: "شرایط مرجوعی",
    Icon: Swap,
  });

  return items;
}

/** Soft service cues below the hero — not a second copy of buy-card guarantees. */
const ASSIST_ITEMS: PdpTrustItem[] = [
  {
    key: "shipping",
    title: "ارسال سریع",
    desc: "پوشش سراسر کشور",
    Icon: Send,
  },
  {
    key: "support",
    title: "پشتیبانی کارگاهی",
    desc: "پاسخگویی ۹ تا ۱۹",
    Icon: Call,
  },
  {
    key: "payment",
    title: "پرداخت امن",
    desc: "درگاه رسمی بانکی",
    Icon: Wallet,
  },
];

function SoftCueStrip({
  items,
  label,
  className,
}: {
  items: PdpTrustItem[];
  label: string;
  className?: string;
}) {
  return (
    <aside
      aria-label={label}
      className={cn(
        "relative overflow-hidden rounded-[1.1rem] bg-gradient-to-l from-[#D02327]/[0.06] via-secondary/40 to-transparent",
        className,
      )}
    >
      <span
        aria-hidden
        className="absolute inset-y-2.5 start-0 w-[3px] rounded-full bg-[#D02327]"
      />

      <ul
        className={cn(
          "grid gap-0 ps-3",
          items.length >= 4
            ? "sm:grid-cols-2 lg:grid-cols-4"
            : "sm:grid-cols-3",
        )}
      >
        {items.map(({ key, title, desc, Icon }, i) => (
          <li
            key={key}
            className={cn(
              "group relative flex items-center gap-2.5 px-3 py-2.5",
              i > 0 &&
                "sm:before:absolute sm:before:inset-y-2 sm:before:start-0 sm:before:w-px sm:before:bg-steel/15",
            )}
          >
            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[#D02327]/10 transition-transform duration-300 group-hover:scale-105 group-hover:bg-[#D02327]/18">
              <Icon set="bold" size="small" primaryColor="#D02327" />
            </span>
            <div className="min-w-0 leading-tight">
              <p className="text-[13px] font-bold tracking-tight text-foreground">
                {title}
              </p>
              <p className="mt-0.5 text-[11px] font-medium text-steel">{desc}</p>
            </div>
          </li>
        ))}
      </ul>
    </aside>
  );
}

/** @deprecated Prefer buy-card trust rows; kept for tests / rare reuse. */
export function ProductTrustStrip({
  warrantyText,
  isOriginal = false,
  className,
}: {
  warrantyText?: string | null;
  isOriginal?: boolean;
  className?: string;
}) {
  return (
    <SoftCueStrip
      label="اعتماد خرید"
      className={className}
      items={buildPdpTrustItems({ warrantyText, isOriginal })}
    />
  );
}

/** Below-hero strip: delivery / support / payment — complements buy-card guarantees. */
export function PdpAssistStrip({ className }: { className?: string }) {
  return (
    <SoftCueStrip
      label="خدمات خرید"
      className={className}
      items={ASSIST_ITEMS}
    />
  );
}
