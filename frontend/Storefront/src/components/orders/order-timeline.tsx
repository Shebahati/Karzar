"use client";

import { motion } from "framer-motion";
import { TickSquare } from "react-iconly";
import { cn } from "@/lib/utils";
import type { OrderTrackingEvent } from "@/types/order";

/** Soft horizontal order timeline (decision 6-B) — mobile-friendly, not a tall stack. */
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
        <p className="mb-4 rounded-lg bg-secondary px-3 py-2 text-xs leading-6 text-muted-foreground">
          <span className="font-bold text-foreground">تخمینی — </span>
          این مراحل بر اساس وضعیت فعلی سفارش ساخته شده‌اند و تاریخچهٔ رسمی سرور نیستند.
        </p>
      )}

      <ol className="-mx-1 flex items-stretch gap-0 overflow-x-auto px-1 pb-1 [scrollbar-width:thin]">
        {events.map((event, i) => {
          const complete = event.is_complete ?? i === 0;
          const current = event.is_current ?? false;
          const pending = !complete && !current;
          const showConnector = i < events.length - 1;

          return (
            <li
              key={`${event.status}-${i}`}
              className="relative flex min-w-[4.75rem] flex-1 flex-col items-center px-1 sm:min-w-0"
            >
              <div className="relative flex w-full items-center justify-center">
                {showConnector && (
                  <span
                    aria-hidden
                    className={cn(
                      "absolute start-1/2 top-1/2 z-0 h-0.5 w-full -translate-y-1/2",
                      complete ? "bg-primary/35" : "bg-border",
                    )}
                  />
                )}
                <motion.span
                  initial={{ scale: 0.85, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ delay: i * 0.06 }}
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
              </div>

              <div className="mt-2 w-full min-w-0 text-center">
                <p
                  className={cn(
                    "text-[11px] font-bold leading-5 sm:text-xs",
                    current ? "text-primary" : complete ? "text-foreground" : "text-muted-foreground",
                  )}
                >
                  {event.status_label}
                  {estimated && pending ? (
                    <span className="mt-0.5 block text-[10px] font-medium text-muted-foreground">
                      (تخمینی)
                    </span>
                  ) : null}
                </p>
                {event.description && (current || complete) ? (
                  <p className="mt-1 hidden text-[10px] leading-5 text-muted-foreground sm:line-clamp-2 sm:block">
                    {event.description}
                  </p>
                ) : null}
                {event.occurred_at && complete && !estimated ? (
                  <p className="mt-1 text-[10px] text-muted-foreground/80 tnum">
                    {new Date(event.occurred_at).toLocaleString("fa-IR")}
                  </p>
                ) : null}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
