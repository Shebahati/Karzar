"use client";

import { useState } from "react";
import { TickSquare, CloseSquare, Document } from "react-iconly";
import { cn } from "@/lib/utils";
import { getFeatureLabel } from "@/lib/feature-labels";
import {
  filterEditorialDescription,
  hasRenderableSpecs,
} from "@/lib/pdp-description";
import type { ProductSpecifications } from "@/types/product";

type TabKey = "specs" | "features" | "dimensions";

export function ProductSpecTabs({
  specifications,
  description,
  shortDescription,
}: {
  specifications: ProductSpecifications | null | undefined;
  description: string | null;
  shortDescription?: string | null;
}) {
  const tech = specifications?.technical_specs ?? [];
  const dims = specifications?.dimensions ?? [];
  const features = Object.entries(specifications?.features ?? {});
  const editorial = filterEditorialDescription(
    description,
    specifications,
    shortDescription,
  );
  const showSpecs = hasRenderableSpecs(specifications);

  const allTabs: { key: TabKey; label: string; count: number }[] = [
    { key: "specs", label: "مشخصات فنی", count: tech.length },
    { key: "features", label: "ویژگی‌ها", count: features.length },
    { key: "dimensions", label: "ابعاد", count: dims.length },
  ];
  const available = allTabs.filter((t) => t.count > 0);
  const [tab, setTab] = useState<TabKey>(available[0]?.key ?? "specs");

  if (!showSpecs && !editorial) return null;

  return (
    <div className="space-y-6">
      {showSpecs ? (
        <div className="overflow-hidden rounded-2xl border border-border/55 bg-card shadow-soft">
          {available.length > 1 ? (
            <div
              role="tablist"
              aria-label="بخش‌های مشخصات"
              className="flex gap-1 border-b border-border/50 bg-secondary/50 p-1.5"
            >
              {available.map((t) => (
                <button
                  key={t.key}
                  type="button"
                  role="tab"
                  aria-selected={tab === t.key}
                  onClick={() => setTab(t.key)}
                  className={cn(
                    "flex-1 rounded-lg py-2.5 text-sm font-bold transition-colors",
                    tab === t.key
                      ? "bg-card text-primary shadow-soft"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {t.label}
                  <span className="ms-1.5 text-xs font-medium text-muted-foreground tnum">
                    ({t.count})
                  </span>
                </button>
              ))}
            </div>
          ) : (
            <div className="border-b border-border/50 px-5 py-3 sm:px-7">
              <h3 className="text-sm font-bold text-foreground">
                {available[0]?.label ?? "مشخصات فنی"}
              </h3>
              <p className="mt-0.5 text-xs text-muted-foreground">
                منبع مشخصات فنی محصول (جدول مشخصات)
              </p>
            </div>
          )}

          <div className="p-2 sm:p-3">
            {tab === "specs" && <KeyValueTable items={tech} />}
            {tab === "dimensions" && <KeyValueTable items={dims} unit="mm" />}
            {tab === "features" && <FeatureList features={features} />}
          </div>
        </div>
      ) : null}

      {editorial ? (
        <article
          aria-labelledby="pdp-editorial-heading"
          className={cn(
            "relative overflow-hidden rounded-[1.25rem]",
            "bg-[linear-gradient(165deg,#FFFFFF_0%,#F8F7F5_48%,#F4F3F1_100%)]",
            "ring-1 ring-steel/[0.08]",
            "shadow-[0_18px_40px_-32px_rgba(94,95,94,0.45)]",
          )}
        >
          <span
            aria-hidden
            className="pointer-events-none absolute inset-0"
            style={{
              background: `
                radial-gradient(48% 55% at 100% 0%, rgba(208,35,39,0.07), transparent 70%),
                radial-gradient(42% 50% at 0% 100%, rgba(94,95,94,0.045), transparent 68%)
              `,
            }}
          />
          <span
            aria-hidden
            className="absolute inset-y-3 start-0 w-[3px] rounded-full bg-[#D02327]/85"
          />

          <div className="relative px-5 py-5 sm:px-7 sm:py-6">
            <header className="flex items-start gap-3">
              <span
                aria-hidden
                className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[#D02327]/[0.09] ring-1 ring-inset ring-[#D02327]/12"
              >
                <Document set="bold" size="small" primaryColor="#D02327" />
              </span>
              <div className="min-w-0">
                <h3
                  id="pdp-editorial-heading"
                  className="text-[15px] font-bold tracking-tight text-foreground sm:text-base"
                >
                  توضیحات
                </h3>
                <p className="mt-0.5 text-[11px] font-medium leading-relaxed text-steel sm:text-xs">
                  متن تحریریه — جدا از جدول مشخصات فنی
                </p>
              </div>
            </header>

            <div
              aria-hidden
              className="mt-4 h-px w-full bg-gradient-to-l from-[#D02327]/20 via-steel/15 to-transparent sm:mt-5"
            />

            <p
              className={cn(
                "mt-4 whitespace-pre-line text-[13.5px] font-medium text-foreground/88 sm:mt-5 sm:text-[15px]",
                "leading-[1.95] sm:leading-[2.05]",
                "max-w-[65ch]",
              )}
            >
              {editorial}
            </p>
          </div>
        </article>
      ) : null}
    </div>
  );
}

function KeyValueTable({
  items,
  unit,
}: {
  items: { key: string; value: string }[];
  unit?: string;
}) {
  return (
    <div className="h-scroll max-w-full" dir="rtl">
      <table className="w-full min-w-[280px] border-collapse text-sm">
        <caption className="sr-only">جدول مشخصات فنی</caption>
        <tbody>
          {items.map((item, i) => (
            <tr
              key={`${item.key}-${i}`}
              className={cn(
                "border-b border-border/40 last:border-b-0",
                i % 2 === 0 ? "bg-secondary/35" : "bg-transparent",
              )}
            >
              <th
                scope="row"
                className="w-[42%] px-4 py-3 text-start align-middle font-medium text-muted-foreground sm:px-5"
              >
                {getFeatureLabel(item.key)}
              </th>
              <td className="px-4 py-3 text-start align-middle font-bold text-foreground tnum sm:px-5">
                {item.value}
                {unit ? ` ${unit}` : ""}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FeatureList({
  features,
}: {
  features: [string, boolean | string][];
}) {
  return (
    <ul className="grid gap-2 p-2 sm:grid-cols-2 sm:p-3">
      {features.map(([name, value]) => {
        const enabled = value === true || (typeof value === "string" && value !== "");
        return (
          <li
            key={name}
            className="flex items-center justify-between gap-2 rounded-xl bg-secondary/50 px-4 py-3"
          >
            <span className="flex items-center gap-2 text-sm text-foreground">
              <span className={enabled ? "text-success" : "text-muted-foreground"}>
                {enabled ? (
                  <TickSquare size="small" set="bold" />
                ) : (
                  <CloseSquare size="small" set="light" />
                )}
              </span>
              {getFeatureLabel(name)}
            </span>
            {typeof value === "string" && value !== "" && (
              <span className="text-sm font-bold text-foreground tnum">{value}</span>
            )}
          </li>
        );
      })}
    </ul>
  );
}
