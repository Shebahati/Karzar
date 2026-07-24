"use client";

import { useState } from "react";
import { TickSquare, CloseSquare } from "react-iconly";
import { cn } from "@/lib/utils";
import { getFeatureLabel } from "@/lib/feature-labels";
import type { ProductSpecifications } from "@/types/product";

type TabKey = "specs" | "features" | "dimensions";

export function ProductSpecTabs({
  specifications,
  description,
}: {
  specifications: ProductSpecifications;
  description: string | null;
}) {
  const tech = specifications.technical_specs ?? [];
  const dims = specifications.dimensions ?? [];
  const features = Object.entries(specifications.features ?? {});

  const allTabs: { key: TabKey; label: string; count: number }[] = [
    { key: "specs", label: "مشخصات فنی", count: tech.length },
    { key: "features", label: "ویژگی‌ها", count: features.length },
    { key: "dimensions", label: "ابعاد", count: dims.length },
  ];
  const available = allTabs.filter((t) => t.count > 0);

  const [tab, setTab] = useState<TabKey>(available[0]?.key ?? "specs");

  return (
    <div className="rounded-2xl bg-card p-5 shadow-soft sm:p-7">
      {description && (
        <p className="mb-6 text-sm leading-8 text-foreground/90">{description}</p>
      )}

      {available.length > 0 && (
        <>
          <div className="flex gap-1 rounded-xl bg-secondary p-1">
            {available.map((t) => (
              <button
                key={t.key}
                type="button"
                onClick={() => setTab(t.key)}
                className={cn(
                  "flex-1 rounded-lg py-2.5 text-sm font-bold transition-colors",
                  tab === t.key
                    ? "bg-white text-primary shadow-soft"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {t.label}
              </button>
            ))}
          </div>

          <div className="mt-5">
            {tab === "specs" && <KeyValueList items={tech} />}
            {tab === "dimensions" && <KeyValueList items={dims} unit="mm" />}
            {tab === "features" && <FeatureList features={features} />}
          </div>
        </>
      )}
    </div>
  );
}

function KeyValueList({
  items,
  unit,
}: {
  items: { key: string; value: string }[];
  unit?: string;
}) {
  return (
    <dl className="divide-y divide-border/60">
      {items.map((item, i) => (
        <div key={`${item.key}-${i}`} className="flex items-center justify-between py-3">
          <dt className="text-sm text-muted-foreground">{item.key}</dt>
          <dd className="text-sm font-bold text-foreground tnum">
            {item.value}
            {unit ? ` ${unit}` : ""}
          </dd>
        </div>
      ))}
    </dl>
  );
}

function FeatureList({
  features,
}: {
  features: [string, boolean | string][];
}) {
  return (
    <ul className="grid gap-2.5 sm:grid-cols-2">
      {features.map(([name, value]) => {
        const enabled = value === true || (typeof value === "string" && value !== "");
        return (
          <li
            key={name}
            className="flex items-center justify-between gap-2 rounded-xl bg-secondary px-4 py-3"
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
              <span className="text-sm font-bold text-foreground">{value}</span>
            )}
          </li>
        );
      })}
    </ul>
  );
}
