"use client";

import { Document, Send, ShieldDone, Swap } from "react-iconly";
import { cn } from "@/lib/utils";

export type PdpTrustItem = {
  key: string;
  title: string;
  desc: string;
  Icon: typeof ShieldDone;
};

/**
 * Trust cues aligned with homepage / footer brand claims.
 * Does not invent certifications — product warranty is optional SoT copy only.
 */
export function buildPdpTrustItems(opts: {
  warrantyText?: string | null;
  isOriginal?: boolean;
}): PdpTrustItem[] {
  const items: PdpTrustItem[] = [
    {
      key: "authenticity",
      title: "ضمانت اصالت کالا",
      desc: opts.isOriginal
        ? "کالای اصلی از مسیر نمایندگی رسمی"
        : "عرضه از مسیر نمایندگی‌های رسمی",
      Icon: ShieldDone,
    },
  ];

  if (opts.warrantyText?.trim()) {
    items.push({
      key: "warranty",
      title: opts.warrantyText.trim(),
      desc: "مطابق شرایط گارانتی محصول",
      Icon: Document,
    });
  }

  items.push(
    {
      key: "return",
      title: "۷ روز ضمانت بازگشت",
      desc: "در صورت وجود شرایط مرجوعی",
      Icon: Swap,
    },
    {
      key: "shipping",
      title: "ارسال مطمئن",
      desc: "بسته‌بندی استاندارد به سراسر کشور",
      Icon: Send,
    },
  );

  return items;
}

export function ProductTrustStrip({
  warrantyText,
  isOriginal = false,
  className,
}: {
  warrantyText?: string | null;
  isOriginal?: boolean;
  className?: string;
}) {
  const items = buildPdpTrustItems({ warrantyText, isOriginal });

  return (
    <aside
      aria-label="اعتماد خرید"
      className={cn(
        "overflow-hidden rounded-2xl border border-border/55 bg-gradient-to-l from-secondary/80 via-card to-card",
        className,
      )}
    >
      <ul className="grid gap-px bg-border/40 sm:grid-cols-2 lg:grid-cols-4">
        {items.map(({ key, title, desc, Icon }) => (
          <li
            key={key}
            className="flex items-start gap-3 bg-card/95 px-4 py-3.5 sm:px-4 sm:py-4"
          >
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-accent text-primary">
              <Icon set="bold" primaryColor="#C22026" />
            </span>
            <div className="min-w-0">
              <p className="text-sm font-bold leading-6 text-foreground">{title}</p>
              <p className="mt-0.5 text-xs leading-5 text-muted-foreground">{desc}</p>
            </div>
          </li>
        ))}
      </ul>
    </aside>
  );
}
