"use client";

import { useMemo, useState } from "react";
import {
  configFromCuratedSeed,
  createDefaultProject,
  CURATED_HERO_SEEDS,
  featuredDockCategories,
  HERO_FEATURED_SLOT_COUNT,
  HERO_SLIDE_SLOT_COUNT,
  isSlideFilled,
  useHeroBuilderStore,
} from "@/entities/hero";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

function orbLabel(key: string | null | undefined, dockNames: Map<string, string>) {
  if (!key) return null;
  if (key === "discounts") return "تخفیف‌ها";
  return dockNames.get(key) ?? key;
}

export function HeroSlidePicker({
  onEnter,
  onOpenDock,
}: {
  onEnter: () => void;
  onOpenDock?: () => void;
}) {
  const {
    project,
    selectSlide,
    duplicateSlide,
    removeSlide,
    renameSlide,
    setSlideActive,
    reorderSlide,
    importProject,
    fillSlideFromCurated,
    validationIssues,
  } = useHeroBuilderStore();

  const [seedPickerFor, setSeedPickerFor] = useState<string | null>(null);

  const slides = useMemo(
    () => [...project.slides].sort((a, b) => a.sortOrder - b.sortOrder),
    [project.slides],
  );

  const dockNames = useMemo(() => {
    const map = new Map<string, string>();
    for (const c of project.categoryDock?.categories ?? []) {
      map.set(c.key, c.name);
    }
    return map;
  }, [project.categoryDock]);

  const featuredCount = featuredDockCategories(
    project.categoryDock ?? { categories: [] },
  ).length;
  const filledCount = slides.filter(isSlideFilled).length;
  const issues = validationIssues();
  const usedOrbKeys = new Set(
    slides.map((s) => s.config.linkedOrbKey).filter(Boolean) as string[],
  );

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-1 pb-8">
      <header className="rounded-2xl border border-[#E8E8E8] bg-white px-6 py-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 max-w-xl">
            <p className="text-[11px] font-bold tracking-wide text-[#5E5F5E]">
              طراحی هیرو کارزار
            </p>
            <h1 className="mt-1 text-2xl font-black text-[#1A1A1A]">
              ۶ اسلاید ثابت
            </h1>
            <p className="mt-2 text-sm leading-relaxed text-[#5E5F5E]">
              دقیقاً {HERO_SLIDE_SLOT_COUNT} اسلاید برای کاروسل، و{" "}
              {HERO_FEATURED_SLOT_COUNT} پاور داک پایین. اتصال دسته ↔ اسلاید با شناسه
              پایدار است — جابه‌جایی ترتیب اسلایدها داک را به هم نمی‌ریزد.
            </p>
          </div>

          <div className="flex flex-col items-stretch gap-2 sm:items-end">
            <div className="flex flex-wrap justify-end gap-2">
              {onOpenDock ? (
                <Button type="button" variant="outline" onClick={onOpenDock}>
                  داک پاور ({featuredCount}/{HERO_FEATURED_SLOT_COUNT})
                </Button>
              ) : null}
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  importProject(createDefaultProject());
                  toast.success("پکیج ۶ اسلایدی پیش‌فرض بارگذاری شد");
                }}
              >
                بارگذاری پیش‌فرض
              </Button>
            </div>
            <div
              className={cn(
                "rounded-xl px-3 py-2 text-center text-xs font-bold",
                filledCount === HERO_SLIDE_SLOT_COUNT
                  ? "bg-[#D02327]/10 text-[#D02327]"
                  : "bg-[#F5F5F5] text-[#5E5F5E]",
              )}
            >
              {filledCount} از {HERO_SLIDE_SLOT_COUNT} اسلاید آماده
            </div>
          </div>
        </div>

        {issues.length ? (
          <ul className="mt-4 space-y-1.5 rounded-xl bg-[#FFF8F0] px-4 py-3 text-xs font-medium text-[#9A3412]">
            {issues.map((issue) => (
              <li key={issue.code}>• {issue.message}</li>
            ))}
          </ul>
        ) : (
          <p className="mt-4 rounded-xl bg-[#F0FDF4] px-4 py-2.5 text-xs font-bold text-[#166534]">
            آماده انتشار — ۶ اسلاید و داک پاور کامل است.
          </p>
        )}
      </header>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {slides.map((slide, index) => {
          const filled = isSlideFilled(slide);
          const bg =
            filled && slide.config.background.mode === "image"
              ? slide.config.background.imageUrl
              : undefined;
          const selected = project.activeSlideId === slide.id;
          const linked = orbLabel(slide.config.linkedOrbKey, dockNames);
          const picking = seedPickerFor === slide.id;

          return (
            <article
              key={slide.id}
              className={cn(
                "flex flex-col overflow-hidden rounded-2xl border bg-white shadow-sm transition",
                selected ? "border-[#D02327] ring-2 ring-[#D02327]/20" : "border-[#E8E8E8]",
                !filled && "border-dashed",
              )}
            >
              <div className="flex items-center justify-between gap-2 border-b border-[#F0F0F0] px-3 py-2">
                <span className="text-[11px] font-black text-[#5E5F5E]">
                  اسلات {index + 1}
                </span>
                <div className="flex gap-1">
                  <button
                    type="button"
                    className="rounded-md bg-[#F5F5F5] px-2 py-0.5 text-[11px] font-bold disabled:opacity-30"
                    disabled={index === 0}
                    onClick={() => reorderSlide(slide.id, -1)}
                    aria-label="جابه‌جایی به قبل"
                  >
                    ↑
                  </button>
                  <button
                    type="button"
                    className="rounded-md bg-[#F5F5F5] px-2 py-0.5 text-[11px] font-bold disabled:opacity-30"
                    disabled={index === slides.length - 1}
                    onClick={() => reorderSlide(slide.id, 1)}
                    aria-label="جابه‌جایی به بعد"
                  >
                    ↓
                  </button>
                </div>
              </div>

              {filled ? (
                <button
                  type="button"
                  className="relative aspect-[16/10] w-full overflow-hidden bg-[#111] text-start"
                  onClick={() => {
                    selectSlide(slide.id);
                    onEnter();
                  }}
                >
                  {bg ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={bg}
                      alt=""
                      className="h-full w-full object-cover"
                      style={{ objectPosition: slide.config.background.focal || "center" }}
                    />
                  ) : (
                    <div
                      className="h-full w-full"
                      style={{ background: slide.config.background.color }}
                    />
                  )}
                  <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />
                  <div className="absolute inset-x-0 bottom-0 p-3">
                    <div className="text-sm font-bold text-white">
                      {slide.config.typography.title || slide.name}
                    </div>
                    <div className="mt-0.5 line-clamp-1 text-[11px] text-white/75">
                      {slide.config.typography.subtitle}
                    </div>
                  </div>
                  {linked ? (
                    <span className="absolute start-3 top-3 rounded-md bg-[#D02327] px-2 py-1 text-[10px] font-bold text-white">
                      داک · {linked}
                    </span>
                  ) : (
                    <span className="absolute start-3 top-3 rounded-md bg-black/55 px-2 py-1 text-[10px] font-bold text-white/90">
                      بدون اتصال داک
                    </span>
                  )}
                </button>
              ) : (
                <div className="flex aspect-[16/10] flex-col items-center justify-center gap-3 bg-[#FAFAFA] px-4">
                  <p className="text-center text-sm font-bold text-[#5E5F5E]">
                    اسلات خالی
                  </p>
                  <Button
                    type="button"
                    size="sm"
                    onClick={() =>
                      setSeedPickerFor(picking ? null : slide.id)
                    }
                  >
                    انتخاب محتوای آماده
                  </Button>
                </div>
              )}

              {picking ? (
                <div className="border-t border-[#F0F0F0] bg-[#FAFAFA] p-3">
                  <label className="block text-[10px] font-bold text-[#5E5F5E]">
                    از پکیج کارزار
                    <select
                      className="mt-1 h-10 w-full rounded-xl border border-[#E8E8E8] bg-white px-3 text-xs font-bold"
                      defaultValue=""
                      onChange={(e) => {
                        const orbKey = e.target.value;
                        if (!orbKey) return;
                        const seed = CURATED_HERO_SEEDS.find((s) => s.orbKey === orbKey);
                        if (!seed) return;
                        fillSlideFromCurated(
                          slide.id,
                          configFromCuratedSeed(seed),
                          seed.name,
                        );
                        setSeedPickerFor(null);
                        toast.success(`اسلات ${index + 1} پر شد`);
                      }}
                    >
                      <option value="">— انتخاب کنید —</option>
                      {CURATED_HERO_SEEDS.map((seed) => (
                        <option
                          key={seed.orbKey}
                          value={seed.orbKey}
                          disabled={usedOrbKeys.has(seed.orbKey)}
                        >
                          {seed.name}
                          {usedOrbKeys.has(seed.orbKey) ? " (در حال استفاده)" : ""}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
              ) : null}

              {filled ? (
                <div className="flex flex-col gap-2 p-3">
                  <input
                    className="h-9 rounded-xl border border-[#E8E8E8] bg-[#FAFAFA] px-3 text-sm font-bold outline-none focus:border-[#D02327]/40"
                    value={slide.name}
                    onChange={(e) => renameSlide(slide.id, e.target.value)}
                  />
                  <div className="grid grid-cols-2 gap-1.5">
                    <Button
                      type="button"
                      size="sm"
                      onClick={() => {
                        selectSlide(slide.id);
                        onEnter();
                      }}
                    >
                      ویرایش
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        const ok = duplicateSlide(slide.id);
                        if (!ok) {
                          toast.error("هر ۶ اسلات پر است — اول یکی را خالی کنید");
                          return;
                        }
                        toast.success("در اسلات خالی کپی شد");
                      }}
                    >
                      کپی
                    </Button>
                  </div>
                  <div className="flex items-center justify-between gap-2">
                    <button
                      type="button"
                      className={cn(
                        "rounded-lg px-2 py-1 text-[11px] font-bold",
                        slide.isActive
                          ? "bg-[#D02327]/10 text-[#D02327]"
                          : "bg-[#F5F5F5] text-[#5E5F5E]",
                      )}
                      onClick={() => setSlideActive(slide.id, !slide.isActive)}
                    >
                      {slide.isActive ? "فعال در سایت" : "مخفی"}
                    </button>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        removeSlide(slide.id);
                        toast.message(`اسلات ${index + 1} خالی شد`);
                      }}
                    >
                      خالی کردن
                    </Button>
                  </div>
                </div>
              ) : null}
            </article>
          );
        })}
      </div>

      <p className="text-center text-xs text-[#5E5F5E]">
        نمی‌توان اسلاید هفتم ساخت. برای جایگزینی، اسلات را خالی کنید و دوباره پر کنید.
      </p>
    </div>
  );
}
