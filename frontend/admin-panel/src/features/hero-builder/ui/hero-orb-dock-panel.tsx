"use client";

import {
  DEFAULT_CATEGORY_DOCK,
  featuredDockCategories,
  HERO_FEATURED_SLOT_COUNT,
  isSpecialDockOrb,
  useHeroBuilderStore,
} from "@/entities/hero";
import { Button } from "@/components/ui/button";
import { PanelSection } from "@/shared/ui";
import { cn } from "@/lib/utils";

/** Compact per-slide summary — full control lives in HeroDockManager. */
export function HeroOrbDockPanel() {
  const store = useHeroBuilderStore();
  const dock = store.project.categoryDock ?? DEFAULT_CATEGORY_DOCK;
  const featured = featuredDockCategories(dock);

  return (
    <PanelSection
      title="داک هیرو"
      hint={`${featured.length}/${HERO_FEATURED_SLOT_COUNT} پاور — مدیریت کامل در «داک دسته‌ها»`}
      defaultOpen
    >
      <p className="text-[11px] leading-relaxed text-muted-foreground">
        پنج اسلات پایین هیرو. اسلات راست = تخفیف‌ها. برای جابه‌جایی و انتشار، صفحهٔ داک را باز کنید.
      </p>

      <div className="space-y-1.5">
        {featured.map((orb, i) => (
          <div
            key={orb.key}
            className={cn(
              "flex items-center gap-2 rounded-xl px-2.5 py-2 ring-1 ring-inset",
              isSpecialDockOrb(orb)
                ? "bg-primary/8 ring-primary/25"
                : "bg-muted/60 ring-border/70",
            )}
          >
            <span className="grid h-7 w-7 place-items-center rounded-full bg-primary text-[10px] font-black text-white">
              {i + 1}
            </span>
            <div className="min-w-0 flex-1 truncate text-xs font-bold">{orb.name}</div>
            {isSpecialDockOrb(orb) ? (
              <span className="text-[9px] font-bold text-primary">ویژه</span>
            ) : null}
          </div>
        ))}
        {featured.length < HERO_FEATURED_SLOT_COUNT ? (
          <p className="text-[10px] text-amber-700">
            {HERO_FEATURED_SLOT_COUNT - featured.length} اسلات خالی — از «داک دسته‌ها» پر کنید
          </p>
        ) : null}
      </div>

      <Button type="button" variant="secondary" className="w-full" onClick={store.syncSlidesFromDock}>
        همگام‌سازی اسلایدها با پاورها
      </Button>
    </PanelSection>
  );
}
