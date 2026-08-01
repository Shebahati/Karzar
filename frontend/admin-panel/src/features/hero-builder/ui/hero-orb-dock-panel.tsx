"use client";

import { DEFAULT_CATEGORY_DOCK, featuredDockCategories, useHeroBuilderStore } from "@/entities/hero";
import { Button } from "@/components/ui/button";
import { PanelSection } from "@/shared/ui";
import { cn } from "@/lib/utils";

const ICON_OPTIONS = [
  "Scan",
  "Discovery",
  "Setting",
  "Work",
  "Category",
  "Edit",
  "Filter2",
  "TickSquare",
  "Bag",
  "ShieldDone",
  "Graph",
  "Buy",
] as const;

/** Compact per-slide panel — full control lives in HeroDockManager. */
export function HeroOrbDockPanel() {
  const store = useHeroBuilderStore();
  const dock = store.project.categoryDock ?? DEFAULT_CATEGORY_DOCK;
  const featured = featuredDockCategories(dock);
  const featuredKeys = new Set(featured.map((c) => c.key));

  return (
    <PanelSection
      title="داک دسته‌بندی هیرو"
      hint="۶ اسلات پاور هیرو — برای مدیریت کامل از «داک دسته‌ها» استفاده کنید"
      defaultOpen
    >
      <p className="text-[11px] leading-relaxed text-muted-foreground">
        حداکثر ۶ دسته در نوار پایین هیرو. بقیه فقط در منوی «همه محصولات». برای انتخاب دقیق
        اسلات‌ها و انتشار، صفحهٔ «داک دسته‌ها» را باز کنید.
      </p>

      <div className="space-y-2">
        <div className="text-xs font-bold text-ink">اسلات‌های پاور ({featured.length}/۶)</div>
        {featured.map((orb, i) => (
          <div
            key={orb.key}
            className="flex items-center gap-2 rounded-xl bg-muted/70 px-2.5 py-2 ring-1 ring-inset ring-border"
          >
            <span className="grid h-7 w-7 place-items-center rounded-full bg-primary text-[10px] font-black text-white">
              {i + 1}
            </span>
            <div className="min-w-0 flex-1">
              <div className="truncate text-xs font-bold">{orb.name}</div>
              <div className="text-[10px] text-muted-foreground" dir="ltr">
                {orb.icon} · {orb.productCount}
              </div>
            </div>
            <button
              type="button"
              className="rounded-lg bg-card px-2 py-1 text-[10px] font-bold disabled:opacity-40"
              disabled={i === 0}
              onClick={() => store.moveFeaturedOrb(orb.key, -1)}
            >
              ↑
            </button>
            <button
              type="button"
              className="rounded-lg bg-card px-2 py-1 text-[10px] font-bold disabled:opacity-40"
              disabled={i === featured.length - 1}
              onClick={() => store.moveFeaturedOrb(orb.key, 1)}
            >
              ↓
            </button>
            <button
              type="button"
              className="rounded-lg bg-card px-2 py-1 text-[10px] font-bold text-primary"
              onClick={() => store.setOrbFeaturedOrder(orb.key, null)}
            >
              حذف
            </button>
          </div>
        ))}
        {featured.length < 6 ? (
          <p className="text-[10px] text-amber-700">
            {6 - featured.length} اسلات خالی — از لیست زیر «افزودن به داک هیرو»
          </p>
        ) : null}
      </div>

      <div className="space-y-2">
        <div className="text-xs font-bold text-ink">همه دسته‌های منو</div>
        {dock.categories.map((orb) => {
          const isFeatured = featuredKeys.has(orb.key);
          return (
            <div
              key={orb.key}
              className={cn(
                "space-y-2 rounded-2xl p-3 ring-1 ring-inset",
                isFeatured ? "bg-primary/5 ring-primary/30" : "bg-card ring-border",
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <input
                  className="h-9 flex-1 rounded-xl bg-muted px-3 text-sm font-bold outline-none"
                  value={orb.name}
                  onChange={(e) => store.updateOrb(orb.key, { name: e.target.value })}
                />
                <button
                  type="button"
                  className={cn(
                    "shrink-0 rounded-lg px-2 py-1.5 text-[10px] font-bold",
                    isFeatured
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-ink disabled:opacity-40",
                  )}
                  disabled={!isFeatured && featured.length >= 6}
                  onClick={() =>
                    store.setOrbFeaturedOrder(
                      orb.key,
                      isFeatured ? null : featured.length,
                    )
                  }
                >
                  {isFeatured ? "پاور ✓" : "افزودن به داک هیرو"}
                </button>
              </div>
              <textarea
                className="min-h-[56px] w-full rounded-xl bg-muted px-3 py-2 text-[11px] leading-relaxed outline-none"
                value={orb.subtitle}
                onChange={(e) => store.updateOrb(orb.key, { subtitle: e.target.value })}
              />
              <div className="grid grid-cols-2 gap-2">
                <label className="text-[10px] text-muted-foreground">
                  آیکون
                  <select
                    className="mt-1 h-9 w-full rounded-xl bg-card px-2 text-xs font-bold shadow-soft"
                    value={orb.icon}
                    onChange={(e) => store.updateOrb(orb.key, { icon: e.target.value })}
                  >
                    {ICON_OPTIONS.map((icon) => (
                      <option key={icon} value={icon}>
                        {icon}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="text-[10px] text-muted-foreground">
                  تعداد نمایشی
                  <input
                    type="number"
                    className="mt-1 h-9 w-full rounded-xl bg-card px-2 text-xs font-bold shadow-soft"
                    value={orb.productCount}
                    onChange={(e) =>
                      store.updateOrb(orb.key, {
                        productCount: Number(e.target.value) || 0,
                      })
                    }
                  />
                </label>
              </div>
              <label className="block text-[10px] text-muted-foreground">
                تصویر هیرو
                <input
                  dir="ltr"
                  className="mt-1 h-9 w-full rounded-xl bg-card px-2 text-xs font-medium shadow-soft"
                  value={orb.heroImage}
                  onChange={(e) => store.updateOrb(orb.key, { heroImage: e.target.value })}
                />
              </label>
            </div>
          );
        })}
      </div>

      <Button type="button" className="w-full" onClick={store.syncSlidesFromDock}>
        همگام‌سازی اسلایدها با داک پاور
      </Button>
      <p className="text-[10px] text-muted-foreground">
        بعد از جابه‌جایی پاورها، این دکمه عنوان/تصویر/زیرنویس اسلایدها را از داک می‌سازد.
      </p>
    </PanelSection>
  );
}
