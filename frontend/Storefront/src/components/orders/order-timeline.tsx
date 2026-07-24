"use client";

import { motion } from "framer-motion";
import { TickSquare } from "react-iconly";
import { cn } from "@/lib/utils";
import type { OrderTrackingEvent } from "@/types/order";

/** Rich order timeline (decision 6-B). */
export function OrderTimeline({
  events,
  estimated = false,
}: {
  events: OrderTrackingEvent[];
  /** When true, steps were inferred from status (not server history). */
  estimated?: boolean;
}) {
  if (!events.length) return null;

  return (
    <div>
      {estimated && (
        <p className="mb-3 rounded-lg bg-secondary px-3 py-2 text-xs leading-6 text-muted-foreground">
          <span className="font-bold text-foreground">تخمینی — </span>
          این مراحل بر اساس وضعیت فعلی سفارش ساخته شده‌اند و تاریخچهٔ رسمی سرور نیستند.
        </p>
      )}
      <ol className="relative mt-1 space-y-0">
        {events.map((event, i) => {
          const complete = event.is_complete ?? i === 0;
          const current = event.is_current ?? false;
          const pending = !complete && !current;

          return (
            <li key={`${event.status}-${i}`} className="relative flex gap-4 pb-6 last:pb-0">
              {i < events.length - 1 && (
                <span
                  className={cn(
                    "absolute start-[15px] top-8 h-[calc(100%-8px)] w-0.5",
                    complete ? "bg-primary/40" : "bg-border",
                  )}
                />
              )}

              <motion.span
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: i * 0.08 }}
                className={cn(
                  "relative z-10 grid h-8 w-8 shrink-0 place-items-center rounded-full border-2",
                  current && "border-primary bg-primary text-primary-foreground shadow-primary-glow",
                  complete && !current && "border-success bg-success text-success-foreground",
                  pending && "border-border bg-secondary text-muted-foreground",
                )}
              >
                {complete && !current ? (
                  <TickSquare size="small" set="bold" />
                ) : (
                  <span className="text-xs font-bold">{i + 1}</span>
                )}
              </motion.span>

              <div className="min-w-0 flex-1 pt-0.5">
                <p
                  className={cn(
                    "text-sm font-bold",
                    current ? "text-primary" : complete ? "text-foreground" : "text-muted-foreground",
                  )}
                >
                  {event.status_label}
                  {estimated && pending && (
                    <span className="ms-2 text-[10px] font-medium text-muted-foreground">(تخمینی)</span>
                  )}
                </p>
                {event.description && (
                  <p className="mt-1 text-xs leading-6 text-muted-foreground">{event.description}</p>
                )}
                {event.occurred_at && complete && !estimated && (
                  <p className="mt-1 text-[10px] text-muted-foreground/80 tnum">
                    {new Date(event.occurred_at).toLocaleString("fa-IR")}
                  </p>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
