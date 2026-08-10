"use client";

import { useId, useState } from "react";
import { ChevronDown } from "react-iconly";
import { cn } from "@/lib/utils";
import type { FaqCategory } from "@/components/legal/faq-content";

/** Multi-open FAQ accordion with expand/collapse-all and subtle open animation. */
export function FaqAccordion({ categories }: { categories: FaqCategory[] }) {
  const baseId = useId();
  const allIds = categories.flatMap((c) => c.items.map((i) => i.id));
  const [openIds, setOpenIds] = useState<Set<string>>(() => new Set());

  const allOpen = allIds.length > 0 && allIds.every((id) => openIds.has(id));

  function toggleItem(id: string) {
    setOpenIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    setOpenIds(allOpen ? new Set() : new Set(allIds));
  }

  return (
    <div className="space-y-8">
      <div className="flex justify-end">
        <button
          type="button"
          onClick={toggleAll}
          aria-expanded={allOpen}
          aria-label={allOpen ? "بستن همه پرسش‌ها" : "باز کردن همه پرسش‌ها"}
          className="group inline-flex items-center gap-2 rounded-xl bg-card/80 py-1.5 ps-3.5 pe-1.5 text-[12px] font-bold text-steel shadow-soft ring-1 ring-inset ring-border/50 transition-colors hover:text-foreground"
        >
          <span className="transition-colors group-hover:text-foreground">
            {allOpen ? "بستن همه" : "باز کردن همه"}
          </span>
          <span
            className={cn(
              "grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[#D02327] text-white transition-transform duration-300 ease-out group-hover:bg-[#B01E22]",
              allOpen && "rotate-180",
            )}
            aria-hidden
          >
            <ChevronDown size="small" set="bold" primaryColor="currentColor" />
          </span>
        </button>
      </div>

      {categories.map((category, ci) => (
        <section
          key={category.id}
          id={category.id}
          className="scroll-mt-28 space-y-3"
        >
          <div className="flex items-center gap-3 px-0.5">
            <span
              aria-hidden
              className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[#D02327]/[0.08] text-[12px] font-bold text-primary tnum"
            >
              {String(ci + 1).padStart(2, "0")}
            </span>
            <h2 className="text-lg font-bold tracking-tight text-foreground sm:text-xl">
              {category.title}
            </h2>
          </div>

          <div className="space-y-3">
            {category.items.map((item, i) => {
              const open = openIds.has(item.id);
              const panelId = `${baseId}-panel-${item.id}`;
              const buttonId = `${baseId}-btn-${item.id}`;

              return (
                <div
                  key={item.id}
                  id={item.id}
                  className="scroll-mt-28 overflow-hidden rounded-2xl bg-card/80 shadow-soft ring-1 ring-inset ring-border/50"
                >
                  <h3 className="m-0 text-base font-bold tracking-tight sm:text-lg">
                    <button
                      type="button"
                      id={buttonId}
                      aria-expanded={open}
                      aria-controls={panelId}
                      onClick={() => toggleItem(item.id)}
                      className="flex w-full items-start gap-3 px-4 py-4 text-start sm:gap-3.5 sm:px-5 sm:py-5"
                    >
                      <span
                        aria-hidden
                        className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-secondary text-[12px] font-bold text-steel tnum"
                      >
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      <span className="min-w-0 flex-1 pt-0.5 text-foreground">
                        {item.question}
                      </span>
                      <span
                        className={cn(
                          "mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-secondary text-steel transition-transform duration-300 ease-out",
                          open && "rotate-180",
                        )}
                        aria-hidden
                      >
                        <ChevronDown
                          size="small"
                          set="light"
                          primaryColor="#5E5F5E"
                        />
                      </span>
                    </button>
                  </h3>
                  <div
                    id={panelId}
                    role="region"
                    aria-labelledby={buttonId}
                    aria-hidden={!open}
                    className={cn(
                      "grid transition-[grid-template-rows,opacity] duration-300 ease-out",
                      open
                        ? "grid-rows-[1fr] opacity-100"
                        : "grid-rows-[0fr] opacity-0",
                    )}
                  >
                    <div className="overflow-hidden">
                      <div className="border-t border-border/40 px-4 pb-4 pt-3 sm:px-5 sm:pb-5 sm:pt-3">
                        <p className="ps-11 text-sm leading-7 text-muted-foreground sm:ps-12">
                          {item.answer}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
