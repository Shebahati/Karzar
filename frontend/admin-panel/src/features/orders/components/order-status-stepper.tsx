"use client";

import { TickSquare } from "react-iconly";
import { cn } from "@/lib/utils";
import type { OrderDetail, OrderStatus } from "@/types/order";
import {
  getWorkflowSteps,
  isStepActive,
  isStepComplete,
  STATUS_LABELS,
  stepIndex,
} from "@/features/orders/order-workflow";

interface OrderStatusStepperProps {
  order: OrderDetail;
}

export function OrderStatusStepper({ order }: OrderStatusStepperProps) {
  const steps = getWorkflowSteps(order);
  const currentIdx = stepIndex(steps, order.status);
  const isCancelled = order.status === "cancelled";

  return (
    <div className="rounded-2xl border border-border bg-card p-4 shadow-sm sm:p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-bold text-foreground">مراحل {order.mode === "inquiry" ? "استعلام" : "سفارش"}</h3>
        {isCancelled && (
          <span className="rounded-full bg-destructive/10 px-3 py-1 text-xs font-bold text-destructive">
            لغو شده
          </span>
        )}
      </div>

      <ol className="flex flex-col gap-0 sm:flex-row sm:items-start sm:gap-0">
        {steps.map((step, index) => {
          const complete = isStepComplete(steps, order.status, step) || currentIdx > index;
          const active = isStepActive(steps, order.status, step);
          const upcoming = !complete && !active;

          return (
            <li
              key={step}
              className={cn(
                "relative flex flex-1 flex-row items-start gap-3 sm:flex-col sm:items-center sm:text-center",
                index < steps.length - 1 && "pb-6 sm:pb-0",
              )}
            >
              {index < steps.length - 1 && (
                <>
                  <span
                    aria-hidden
                    className={cn(
                      "absolute start-[1.125rem] top-9 h-[calc(100%-2rem)] w-0.5 sm:start-1/2 sm:top-5 sm:h-0.5 sm:w-full sm:-translate-x-1/2",
                      complete ? "bg-primary" : "bg-border",
                    )}
                  />
                </>
              )}

              <span
                className={cn(
                  "relative z-10 grid h-9 w-9 shrink-0 place-items-center rounded-full border-2 text-xs font-bold transition-colors",
                  complete && "border-primary bg-primary text-primary-foreground",
                  active && !complete && "border-primary bg-accent text-primary",
                  upcoming && "border-border bg-muted text-muted-foreground",
                )}
              >
                {complete ? <TickSquare set="bold" size={18} /> : index + 1}
              </span>

              <div className="min-w-0 flex-1 pt-0.5 sm:pt-3">
                <p
                  className={cn(
                    "text-xs font-bold sm:text-sm",
                    active ? "text-primary" : complete ? "text-foreground" : "text-muted-foreground",
                  )}
                >
                  {STATUS_LABELS[step]}
                </p>
                {active && (
                  <p className="mt-1 text-[11px] leading-5 text-muted-foreground sm:text-xs">
                    مرحله فعلی
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
