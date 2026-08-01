"use client";

import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { ArrowDown, ArrowUp, Delete, Plus } from "react-iconly";
import {
  DEFAULT_CATEGORY_DOCK,
  featuredDockCategories,
  HERO_FEATURED_SLOT_COUNT,
  isSpecialDockOrb,
  useHeroBuilderStore,
} from "@/entities/hero";
import type { PublishedHeroPack } from "@/entities/hero";
import { isCategoryIconUrl, resolveCategoryIconUrl } from "@/config/category-icons";
import { useCategories } from "@/features/catalog/queries";
import { publishHeroPack } from "../lib/publish-hero";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const SLOT_INDEXES = Array.from(
  { length: HERO_FEATURED_SLOT_COUNT },
  (_, i) => i,
) as number[];

function DockIconPreview({ name, label }: { name: string; label?: string }) {
  const src = resolveCategoryIconUrl({ icon: name, name: label }) ?? name;
  if (isCategoryIconUrl(src)) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img src={src} alt="" className="h-8 w-8 object-contain" draggable={false} />
    );
  }
  return (
    <span className="text-[10px] font-bold text-primary" dir="ltr">
      {name.slice(0, 6)}
    </span>
  );
}

/** Project-level dock manager — outside per-slide settings. */
export function HeroDockManager({ onBack }: { onBack: () => void }) {
  const store = useHeroBuilderStore();
  const { data: tree = [], isLoading: categoriesLoading } = useCategories();
  const dock = store.project.categoryDock ?? DEFAULT_CATEGORY_DOCK;
  const slides = [...store.project.slides].sort((a, b) => a.sortOrder - b.sortOrder);
  const featured = featuredDockCategories(dock);
  const available = store.dockAvailable;
  const [publishing, setPublishing] = useState(false);
  const [slotPicker, setSlotPicker] = useState<number | null>(null);

  const l1Roots = useMemo(
    () => tree.filter((r) => r.parent_id == null),
    [tree],
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/hero-design/publish", { cache: "no-store" });
        if (!res.ok) return;
        const pack = (await res.json()) as PublishedHeroPack & {
          publishedAt?: string | null;
        };
        if (cancelled || !pack?.categoryDock?.categories?.length) return;
        const current = store.project.categoryDock?.categories ?? [];
        const published = pack.categoryDock.categories;
        const needsHydrate =
          !current.length ||
          current.every((c) => !isCategoryIconUrl(c.icon)) ||
          (current.length &&
            published.length &&
            !current.some((c) =>
              published.some(
                (p) => p.key === c.key || p.name.trim() === c.name.trim(),
              ),
            ));
        if (!needsHydrate) return;
        store.importProject({
          ...store.project,
          categoryDock: { categories: published },
          slides: store.project.slides.length
            ? store.project.slides
            : pack.slides?.length
              ? pack.slides.map((s, i) => ({
                  id: s.id,
                  name: s.name,
                  sortOrder: s.sortOrder ?? i + 1,
                  isActive: s.isActive !== false,
                  mobilePreset: s.mobilePreset,
                  config: s.config,
                }))
              : store.project.slides,
        });
      } catch {
        /* ignore */
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!l1Roots.length) return;
    store.syncCategoryDockFromRoots(l1Roots, { appendNew: false });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [l1Roots]);

  const [mappingDraft, setMappingDraft] = useState<Record<string, string>>(() => {
    const map: Record<string, string> = {};
    featured.forEach((orb, i) => {
      const linked = slides.find((s) => s.config.linkedOrbKey === orb.key);
      map[orb.key] = linked?.id ?? slides[i]?.id ?? "";
    });
    return map;
  });

  useEffect(() => {
    setMappingDraft((prev) => {
      const next = { ...prev };
      featured.forEach((orb, i) => {
        if (!next[orb.key]) {
          const linked = slides.find((s) => s.config.linkedOrbKey === orb.key);
          next[orb.key] = linked?.id ?? slides[i]?.id ?? "";
        }
      });
      return next;
    });
  }, [featured, slides]);

  const availableToAdd = useMemo(() => {
    if (available.length) return available;
    const dockIds = new Set(
      dock.categories.map((c) => c.categoryId).filter((id): id is number => id != null),
    );
    const dockNames = new Set(dock.categories.map((c) => c.name.trim()));
    return l1Roots.filter(
      (r) => !dockIds.has(r.id) && !dockNames.has(r.name.trim()),
    );
  }, [available, dock.categories, l1Roots]);

  const nonFeatured = useMemo(
    () => dock.categories.filter((c) => c.featuredOrder == null),
    [dock.categories],
  );

  const featuredBySlot = useMemo(() => {
    const map = new Map(featured.map((c) => [c.featuredOrder!, c]));
    return SLOT_INDEXES.map((slot) => map.get(slot) ?? null);
  }, [featured]);

  const addToHeroDock = (key: string, preferredSlot?: number) => {
    if (featured.some((c) => c.key === key)) {
      if (preferredSlot != null) store.assignFeaturedSlot(key, preferredSlot);
      return;
    }
    if (featured.length >= HERO_FEATURED_SLOT_COUNT && preferredSlot == null) {
      toast.error("هر ۵ اسلات پر است — اول یکی را خالی کنید");
      return;
    }
    if (preferredSlot != null) {
      store.assignFeaturedSlot(key, preferredSlot);
    } else {
      store.setOrbFeaturedOrder(key, featured.length);
    }
    toast.success("به داک هیرو اضافه شد");
  };

  const publishDock = async () => {
    setPublishing(true);
    try {
      Object.entries(mappingDraft).forEach(([orbKey, slideId]) => {
        if (slideId) store.linkSlideToOrb(slideId, orbKey);
      });
      const pack = store.toPublishedPack();
      if (!pack.slides.length) {
        toast.error("حداقل یک اسلاید فعال لازم است");
        return;
      }
      const featuredCount = pack.categoryDock.categories.filter(
        (c) => c.featuredOrder != null,
      ).length;
      const result = await publishHeroPack(pack);
      if (result.fileOk) {
        store.markClean();
        toast.success(`منتشر شد · ${featuredCount}/۵ اسلات پاور روی فروشگاه`);
      } else {
        toast.error(result.detail ?? "انتشار فایل ناموفق بود");
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "خطا در انتشار");
    } finally {
      setPublishing(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-7.5rem)] min-h-[560px] flex-col gap-4">
      <header className="rounded-2xl bg-card px-5 py-4 shadow-soft">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <Button type="button" variant="ghost" size="sm" onClick={onBack}>
              ← بازگشت به اسلایدها
            </Button>
            <h1 className="mt-1 text-xl font-black text-ink">داک هیرو · ۵ پاور</h1>
            <p className="mt-1 max-w-2xl text-sm leading-relaxed text-muted-foreground">
              اسلات ۱ از راست = تخفیف‌ها. بقیه را از دسته‌های L1 پر کنید، به اسلاید وصل کنید، سپس
              منتشر کنید.
              {categoriesLoading
                ? " در حال همگام‌سازی…"
                : ` ${featured.length}/۵ پاور · ${dock.categories.length} در منو · ${availableToAdd.length} قابل افزودن`}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="outline"
              disabled={!l1Roots.length}
              onClick={() => {
                const result = store.syncCategoryDockFromRoots(l1Roots, { appendNew: false });
                toast.success(
                  `همگام شد: ${result.updated} به‌روز · ${result.removed} حذف · ${result.available} قابل افزودن`,
                );
              }}
            >
              همگام با دیتابیس
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                store.syncSlidesFromDock();
                toast.success("اسلایدها با ۵ پاور همگام شدند");
              }}
            >
              ساخت اسلاید از پاورها
            </Button>
            <Button type="button" disabled={publishing} onClick={() => void publishDock()}>
              {publishing ? "در حال انتشار…" : "انتشار روی سایت"}
            </Button>
          </div>
        </div>
      </header>

      {/* Visual strip — matches storefront RTL dock order */}
      <section className="rounded-2xl bg-card p-4 shadow-soft">
        <div className="mb-3 flex items-baseline justify-between gap-2">
          <h2 className="text-sm font-black text-ink">نوار پاور (راست ← چپ)</h2>
          <span className="text-[11px] text-muted-foreground">همان ترتیب فروشگاه</span>
        </div>
        <div className="flex flex-wrap justify-center gap-3" dir="rtl">
          {SLOT_INDEXES.map((slot) => {
            const orb = featuredBySlot[slot];
            return (
              <div
                key={slot}
                className={cn(
                  "flex w-[7.5rem] flex-col items-center gap-2 rounded-2xl px-2 py-3 ring-1 ring-inset",
                  orb ? "bg-primary/5 ring-primary/20" : "bg-muted/40 ring-dashed ring-border",
                )}
              >
                <span className="text-[10px] font-bold text-muted-foreground">
                  {slot === 0 ? "۱ · راست" : `${slot + 1}`}
                </span>
                <span className="grid h-12 w-12 place-items-center rounded-full bg-white shadow-soft">
                  {orb ? (
                    <DockIconPreview name={orb.icon} label={orb.name} />
                  ) : (
                    <span className="text-lg text-muted-foreground">+</span>
                  )}
                </span>
                <span className="line-clamp-2 text-center text-[11px] font-bold text-ink">
                  {orb?.name ?? "خالی"}
                </span>
              </div>
            );
          })}
        </div>
      </section>

      <div className="grid min-h-0 flex-1 gap-4 overflow-y-auto lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
        {/* Slot editor */}
        <section className="space-y-3 rounded-2xl bg-card p-4 shadow-soft">
          <div>
            <h2 className="text-sm font-black text-ink">ویرایش ۵ اسلات</h2>
            <p className="mt-1 text-[11px] text-muted-foreground">
              ترتیب، اتصال اسلاید، یا خالی کردن اسلات
            </p>
          </div>

          {SLOT_INDEXES.map((slot) => {
            const orb = featuredBySlot[slot];
            const special = orb ? isSpecialDockOrb(orb) : false;
            return (
              <div
                key={slot}
                className={cn(
                  "rounded-xl p-3 ring-1 ring-inset",
                  orb ? "bg-muted/30 ring-border/80" : "bg-muted/20 ring-dashed ring-border",
                )}
              >
                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      "grid h-8 w-8 shrink-0 place-items-center rounded-full text-xs font-black",
                      orb ? "bg-primary text-white" : "bg-card text-muted-foreground shadow-soft",
                    )}
                  >
                    {slot + 1}
                  </span>
                  {orb ? (
                    <>
                      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-white shadow-soft">
                        <DockIconPreview name={orb.icon} label={orb.name} />
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-sm font-bold">{orb.name}</div>
                        <div className="text-[10px] text-muted-foreground">
                          {special ? "ویژه · بدون دسته L1" : orb.slugHint || orb.key}
                        </div>
                      </div>
                      <div className="flex shrink-0 gap-1">
                        <button
                          type="button"
                          aria-label="جابه‌جایی به راست"
                          className="grid h-8 w-8 place-items-center rounded-lg bg-card disabled:opacity-40"
                          disabled={slot === 0}
                          onClick={() => store.moveFeaturedOrb(orb.key, -1)}
                        >
                          <ArrowUp size={14} set="light" primaryColor="#5E5F5E" />
                        </button>
                        <button
                          type="button"
                          aria-label="جابه‌جایی به چپ"
                          className="grid h-8 w-8 place-items-center rounded-lg bg-card disabled:opacity-40"
                          disabled={slot >= featured.length - 1}
                          onClick={() => store.moveFeaturedOrb(orb.key, 1)}
                        >
                          <ArrowDown size={14} set="light" primaryColor="#5E5F5E" />
                        </button>
                        {!special ? (
                          <button
                            type="button"
                            aria-label="حذف از داک هیرو"
                            className="grid h-8 w-8 place-items-center rounded-lg bg-card"
                            onClick={() => store.setOrbFeaturedOrder(orb.key, null)}
                          >
                            <Delete size={14} set="light" primaryColor="#D02327" />
                          </button>
                        ) : null}
                      </div>
                    </>
                  ) : (
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-bold text-muted-foreground">اسلات خالی</div>
                    </div>
                  )}
                </div>

                {orb ? (
                  <label className="mt-2 block text-[10px] font-bold text-muted-foreground">
                    اسلاید متصل
                    <select
                      className="mt-1 h-10 w-full rounded-xl bg-card px-3 text-xs font-bold shadow-soft"
                      value={mappingDraft[orb.key] ?? ""}
                      onChange={(e) =>
                        setMappingDraft((m) => ({ ...m, [orb.key]: e.target.value }))
                      }
                    >
                      <option value="">— انتخاب اسلاید —</option>
                      {slides.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name}
                        </option>
                      ))}
                    </select>
                  </label>
                ) : (
                  <div className="mt-2 space-y-2">
                    <Button
                      type="button"
                      size="sm"
                      variant="secondary"
                      className="w-full"
                      disabled={!nonFeatured.length}
                      onClick={() => setSlotPicker(slotPicker === slot ? null : slot)}
                    >
                      <Plus size={14} set="light" />
                      انتخاب دسته برای این اسلات
                    </Button>
                    {slotPicker === slot ? (
                      <select
                        className="h-10 w-full rounded-xl bg-card px-2 text-xs font-bold shadow-soft"
                        defaultValue=""
                        onChange={(e) => {
                          const key = e.target.value;
                          if (!key) return;
                          addToHeroDock(key, slot);
                          setSlotPicker(null);
                        }}
                      >
                        <option value="">— انتخاب —</option>
                        {nonFeatured.map((c) => (
                          <option key={c.key} value={c.key}>
                            {c.name}
                          </option>
                        ))}
                      </select>
                    ) : null}
                  </div>
                )}
              </div>
            );
          })}
        </section>

        {/* Menu + available */}
        <div className="space-y-4">
          <section className="space-y-2 rounded-2xl bg-card p-4 shadow-soft">
            <h2 className="text-sm font-black text-ink">منوی «همه محصولات»</h2>
            <p className="text-[11px] text-muted-foreground">
              اعضا در اورلی هیرو؛ با یک کلیک به اسلات خالی داک می‌روند
            </p>
            <div className="max-h-[22rem] space-y-2 overflow-y-auto pe-1">
              {dock.categories.map((orb) => {
                const isFeatured = orb.featuredOrder != null;
                const special = isSpecialDockOrb(orb);
                return (
                  <div
                    key={orb.key}
                    className={cn(
                      "flex items-center gap-2 rounded-xl px-2.5 py-2 ring-1 ring-inset",
                      isFeatured ? "bg-primary/5 ring-primary/20" : "bg-muted/40 ring-transparent",
                    )}
                  >
                    <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-white shadow-soft">
                      <DockIconPreview name={orb.icon} label={orb.name} />
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-bold">{orb.name}</div>
                      {special ? (
                        <div className="text-[10px] text-primary">اسلات ویژه تخفیف</div>
                      ) : null}
                    </div>
                    <button
                      type="button"
                      className={cn(
                        "shrink-0 rounded-lg px-2.5 py-1.5 text-[10px] font-bold",
                        isFeatured
                          ? "bg-primary text-primary-foreground"
                          : "bg-card text-ink disabled:opacity-40",
                      )}
                      disabled={!isFeatured && featured.length >= HERO_FEATURED_SLOT_COUNT}
                      onClick={() => {
                        if (isFeatured) {
                          if (special) {
                            toast.message("تخفیف‌ها عضو ثابت داک است — فقط اسلات را جابه‌جا کنید");
                            return;
                          }
                          store.setOrbFeaturedOrder(orb.key, null);
                        } else {
                          addToHeroDock(orb.key);
                        }
                      }}
                    >
                      {isFeatured ? `پاور ${orb.featuredOrder! + 1}` : "به داک"}
                    </button>
                    {!special ? (
                      <button
                        type="button"
                        aria-label="حذف از منو"
                        className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-card"
                        onClick={() => {
                          store.removeOrbFromDock(orb.key);
                          toast.message(`«${orb.name}» از منو حذف شد`);
                        }}
                      >
                        <Delete size={14} set="light" primaryColor="#D02327" />
                      </button>
                    ) : null}
                  </div>
                );
              })}
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="w-full"
              disabled={!l1Roots.length}
              onClick={() => {
                const result = store.syncCategoryDockFromRoots(l1Roots, { appendNew: true });
                toast.success(
                  result.added
                    ? `${result.added} دستهٔ جدید به منو اضافه شد`
                    : "دستهٔ جدیدی نبود",
                );
              }}
            >
              افزودن همهٔ L1 جدید به منو
            </Button>
          </section>

          <section className="space-y-2 rounded-2xl bg-card p-4 shadow-soft">
            <h2 className="text-sm font-black text-ink">قابل افزودن از L1</h2>
            {availableToAdd.length ? (
              availableToAdd.map((root) => (
                <div
                  key={root.id}
                  className="flex items-center gap-2 rounded-xl bg-muted/50 px-3 py-2"
                >
                  <div className="min-w-0 flex-1 truncate text-sm font-bold">{root.name}</div>
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    onClick={() => {
                      const ok = store.addOrbToDock(root);
                      if (ok) toast.success(`«${root.name}» به منو اضافه شد`);
                      else toast.error("این دسته از قبل در منو است");
                    }}
                  >
                    <Plus size={14} set="light" />
                    افزودن
                  </Button>
                </div>
              ))
            ) : (
              <p className="text-xs text-muted-foreground">
                {categoriesLoading
                  ? "در حال بارگذاری…"
                  : "همهٔ دسته‌های L1 در منو هستند."}
              </p>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
