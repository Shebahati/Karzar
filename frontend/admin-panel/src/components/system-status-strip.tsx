"use client";

import { useSystemHealth, useSystemReady } from "@/features/system/queries";
import { cn } from "@/lib/utils";

function StatusDot({ ok, label }: { ok: boolean | null; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs">
      <span
        className={cn(
          "h-2 w-2 rounded-full",
          ok === null && "bg-muted-foreground/40",
          ok === true && "bg-success",
          ok === false && "bg-destructive",
        )}
        aria-hidden
      />
      <span className="text-muted-foreground">{label}</span>
      <span className={cn("font-bold", ok === false ? "text-destructive" : "text-foreground")}>
        {ok === null ? "…" : ok ? "سالم" : "مشکل"}
      </span>
    </span>
  );
}

function isHealthyStatus(status: unknown): boolean {
  const value = String(status ?? "").toLowerCase();
  return value === "ok" || value === "healthy" || value === "ready";
}

/** Compact API /health + /ready indicator for the admin dashboard. */
export function SystemStatusStrip() {
  const health = useSystemHealth();
  const ready = useSystemReady();

  const healthOk = health.isError ? false : health.data ? isHealthyStatus(health.data.status) : null;
  const readyOk = ready.isError ? false : ready.data ? isHealthyStatus(ready.data.status) : null;

  const detailBits: string[] = [];
  if (ready.data) {
    if (typeof ready.data.database === "string") detailBits.push(`db: ${ready.data.database}`);
    if (typeof ready.data.redis === "string") detailBits.push(`redis: ${ready.data.redis}`);
    if (ready.data.checks) {
      for (const [k, v] of Object.entries(ready.data.checks)) {
        detailBits.push(`${k}: ${v}`);
      }
    }
  }

  return (
    <div
      role="status"
      className="flex flex-wrap items-center gap-x-5 gap-y-2 rounded-xl border border-border/60 bg-card px-4 py-3 shadow-sm"
    >
      <p className="text-sm font-bold text-foreground">وضعیت سرویس API</p>
      <StatusDot ok={healthOk} label="Health" />
      <StatusDot ok={readyOk} label="Ready" />
      {detailBits.length > 0 && (
        <span className="text-[11px] text-muted-foreground">{detailBits.join(" · ")}</span>
      )}
    </div>
  );
}
