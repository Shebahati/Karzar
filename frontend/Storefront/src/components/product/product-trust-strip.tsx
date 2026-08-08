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
 * Buy-card trust: only real product warranty (warranty_text).
 * Does not invent authenticity / return chips — those live on the shared strip.
 */
export function buildPdpBuyCardTrust(opts: {
  warrantyText?: string | null;
}): PdpTrustItem[] {
  const text = opts.warrantyText?.trim();
  if (!text) return [];
  return [
    {
      key: "warranty",
      title: text,
      desc: "شرایط گارانتی",
      Icon: Document,
    },
  ];
}

/**
 * @deprecated Prefer buildPdpBuyCardTrust for the card and buildPdpStripTrustItems
 * for the shared strip. Kept for tests / rare reuse.
 */
export function buildPdpTrustItems(opts: {
  warrantyText?: string | null;
  isOriginal?: boolean;
}): PdpTrustItem[] {
  return [
    ...buildPdpStripTrustItems({ isOriginal: opts.isOriginal }),
    ...buildPdpBuyCardTrust({ warrantyText: opts.warrantyText }),
  ];
}

const SERVICE_ITEMS: PdpTrustItem[] = [
  {
    key: "shipping",
    title: "ارسال سریع",
    desc: "پوشش سراسر کشور",
    Icon: Send,
  },
  {
    key: "support",
    title: "پشتیبانی کارگاهی",
    desc: "پاسخگویی ۹ تا ۱۸",
    Icon: Call,
  },
  {
    key: "payment",
    title: "پرداخت امن",
    desc: "درگاه رسمی بانکی",
    Icon: Wallet,
  },
];

/** Shared strip: authenticity + return + delivery / support / payment. */
export function buildPdpStripTrustItems(opts?: {
  isOriginal?: boolean;
}): PdpTrustItem[] {
  return [
    {
      key: "authenticity",
      title: "ضمانت اصالت",
      desc: opts?.isOriginal ? "کالای اصلی" : "نمایندگی رسمی",
      Icon: ShieldDone,
    },
    {
      key: "return",
      title: "۷ روز بازگشت",
      desc: "شرایط مرجوعی",
      Icon: Swap,
    },
    ...SERVICE_ITEMS,
  ];
}

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
        "relative overflow-hidden rounded-[1.1rem]",
        className,
      )}
    >
      <ul
        className={cn(
          "grid gap-0",
          items.length >= 5
            ? "sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5"
            : items.length >= 4
              ? "sm:grid-cols-2 lg:grid-cols-4"
              : "sm:grid-cols-3",
        )}
      >
        {items.map(({ key, title, desc, Icon }) => (
          <li
            key={key}
            className="group relative flex items-center gap-2.5 px-3 py-2.5 ps-4"
          >
            <span
              aria-hidden
              className="absolute inset-y-2.5 start-0 w-[3px] rounded-full bg-[#D02327]"
            />
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

/** @deprecated Prefer PdpAssistStrip; kept for tests / rare reuse. */
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

/** Below-hero strip: authenticity / return + delivery / support / payment. */
export function PdpAssistStrip({
  isOriginal = false,
  className,
}: {
  isOriginal?: boolean;
  className?: string;
}) {
  return (
    <SoftCueStrip
      label="خدمات و اعتماد خرید"
      className={className}
      items={buildPdpStripTrustItems({ isOriginal })}
    />
  );
}
