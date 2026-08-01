"use client";

import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { ArrowDown, ArrowUp, Delete, Plus } from "react-iconly";
import {
  DEFAULT_CATEGORY_DOCK,
  featuredDockCategories,
  useHeroBuilderStore,
} from "@/entities/hero";
import type { PublishedHeroPack } from "@/entities/hero";
import { isCategoryIconUrl, resolveCategoryIconUrl } from "@/config/category-icons";
import { useCategories } from "@/features/catalog/queries";
import { publishHeroPack } from "../lib/publish-hero";
import { Button } from "@/components/ui/button";
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
  "Document",
  "Wallet",
  "Send",
  "Chart",
  "TwoUsers",
  "TimeCircle",
] as const;

const SLOT_INDEXES = [0, 1, 2, 3, 4, 5] as const;

function DockIconPreview({ name, label }: { name: string; label?: string }) {
  const src = resolveCategoryIconUrl({ icon: name, name: label }) ?? name;
  if (isCategoryIconUrl(src)) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img src={src} alt="" className="h-7 w-7 object-contain" draggable={false} />
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

  // Hydrate dock from published hero-design.json when local dock is empty/stale.
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
          slides: store.project.slides.length ? store.project.slides : pack.slides?.length
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
        /* ignore — local defaults remain */
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- hydrate once on mount
  }, []);

  // Initial sync once tree arrives — refresh metadata, don't wipe curated dock
  useEffect(() => {
    if (!l1Roots.length) return;
    store.syncCategoryDockFromRoots(l1Roots, { appendNew: false });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- sync once tree arrives
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
    if (featured.length >= 6 && preferredSlot == null) {
      toast.error("هر ۶ اسلات پر است — اول یکی را خالی کنید");
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
        toast.success(
          `منتشر شد · ${featuredCount}/۶ اسلات پاور روی فروشگاه`,
        );
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
      <header className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-card px-5 py-4 shadow-soft">
        <div>
          <Button type="button" variant="ghost" size="sm" onClick={onBack}>
            ← بازگشت
          </Button>
          <h1 className="mt-1 text-xl font-black text-ink">داک دسته‌بندی هیرو</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            دسته‌های L1 را ببینید، دقیقاً ۶تای پایین هیرو را انتخاب کنید، ترتیب بدهید و منتشر کنید.
            {categoriesLoading
              ? " در حال همگام‌سازی…"
              : ` ${dock.categories.length} در منو · ${featured.length}/۶ در داک هیرو · ${availableToAdd.length} قابل افزودن`}
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
                `همگام شد: ${result.updated} به‌روز · ${result.removed} حذف‌شده از DB · ${result.available} قابل افزودن`,
              );
            }}
          >
            همگام با دیتابیس
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={!l1Roots.length}
            onClick={() => {
              const result = store.syncCategoryDockFromRoots(l1Roots, { appendNew: true });
              toast.success(
                result.added
                  ? `${result.added} دستهٔ جدید به منو اضافه شد`
                  : "دستهٔ جدیدی برای افزودن نبود",
              );
            }}
          >
            افزودن همهٔ L1 جدید
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              store.syncSlidesFromDock();
              toast.success("اسلایدها با ۶ پاور همگام شدند");
            }}
          >
            ساخت/به‌روز اسلاید از پاورها
          </Button>
          <Button type="button" disabled={publishing} onClick={() => void publishDock()}>
            {publishing ? "در حال انتشار…" : "انتشار داک روی سایت"}
          </Button>
        </div>
      </header>

      <div className="grid min-h-0 flex-1 gap-4 overflow-y-auto lg:grid-cols-3">
        {/* 6 featured hero slots */}
        <section className="space-y-3 rounded-2xl bg-card p-4 shadow-soft">
          <h2 className="text-sm font-black text-ink">۶ اسلات داک هیرو</h2>
          <p className="text-[11px] text-muted-foreground">
            همین ۶ دسته روی نوار پایین هیرو فروشگاه دیده می‌شوند. اسلات خالی را پر کنید یا ترتیب را عوض کنید.
          </p>

          {SLOT_INDEXES.map((slot) => {
            const orb = featuredBySlot[slot];
            return (
              <div
                key={slot}
                className={cn(
                  "flex min-w-0 flex-col gap-2 rounded-xl p-3 ring-1 ring-inset",
                  orb
                    ? "bg-primary/5 ring-primary/25"
                    : "bg-muted/40 ring-dashed ring-border",
                )}
              >
                <div className="flex min-w-0 items-center gap-2">
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
                      <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-white shadow-soft">
                        <DockIconPreview name={orb.icon} label={orb.name} />
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-sm font-bold">{orb.name}</div>
                        <div className="text-[10px] text-muted-foreground" dir="ltr">
                          slot {slot} · {orb.icon}
                        </div>
                      </div>
                      <div className="flex shrink-0 items-center gap-1">
                        <button
                          type="button"
                          aria-label="بالا"
                          className="grid h-8 w-8 place-items-center rounded-lg bg-card disabled:opacity-40"
                          disabled={slot === 0}
                          onClick={() => store.moveFeaturedOrb(orb.key, -1)}
                        >
                          <ArrowUp size={14} set="light" primaryColor="#5E5F5E" />
                        </button>
                        <button
                          type="button"
                          aria-label="پایین"
                          className="grid h-8 w-8 place-items-center rounded-lg bg-card disabled:opacity-40"
                          disabled={slot >= featured.length - 1}
                          onClick={() => store.moveFeaturedOrb(orb.key, 1)}
                        >
                          <ArrowDown size={14} set="light" primaryColor="#5E5F5E" />
                        </button>
                        <button
                          type="button"
                          aria-label="حذف از داک هیرو"
                          className="grid h-8 w-8 place-items-center rounded-lg bg-card text-primary"
                          onClick={() => store.setOrbFeaturedOrder(orb.key, null)}
                        >
                          <Delete size={14} set="light" primaryColor="#D02327" />
                        </button>
                      </div>
                    </>
                  ) : (
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-bold text-muted-foreground">اسلات خالی</div>
                      <p className="text-[10px] text-muted-foreground">
                        یک دسته از منو انتخاب کنید
                      </p>
                    </div>
                  )}
                </div>

                {orb ? (
                  <select
                    className="h-10 min-w-0 w-full rounded-xl bg-card px-2 text-xs font-bold shadow-soft"
                    value={mappingDraft[orb.key] ?? ""}
                    onChange={(e) =>
                      setMappingDraft((m) => ({ ...m, [orb.key]: e.target.value }))
                    }
                  >
                    <option value="">— اتصال اسلاید —</option>
                    {slides.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                ) : (
                  <div className="space-y-2">
                    <Button
                      type="button"
                      size="sm"
                      variant="secondary"
                      className="w-full"
                      disabled={!nonFeatured.length}
                      onClick={() => setSlotPicker(slotPicker === slot ? null : slot)}
                    >
                      <Plus size={14} set="light" />
                      افزودن به داک هیرو
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
                        <option value="">— انتخاب دسته —</option>
                        {nonFeatured.map((c) => (
                          <option key={c.key} value={c.key}>
                            {c.name}
                          </option>
                        ))}
                      </select>
                    ) : null}
                    {!nonFeatured.length ? (
                      <p className="text-[10px] text-amber-700">
                        همهٔ اعضای منو پاور هستند یا منو خالی است — از ستون سوم دسته اضافه کنید.
                      </p>
                    ) : null}
                  </div>
                )}
              </div>
            );
          })}
        </section>

        {/* Dock members (all-categories menu) */}
        <section className="space-y-3 rounded-2xl bg-card p-4 shadow-soft">
          <h2 className="text-sm font-black text-ink">همه دسته‌های منو (از L1)</h2>
          <p className="text-[11px] text-muted-foreground">
            اعضای منوی «همه محصولات» — با «افزودن به داک هیرو» وارد یکی از ۶ اسلات می‌شوند
          </p>
          {dock.categories.map((orb, idx) => {
            const isFeatured = orb.featuredOrder != null;
            return (
              <div
                key={orb.key}
                className={cn(
                  "min-w-0 space-y-2 rounded-xl p-3 ring-1 ring-inset",
                  isFeatured ? "bg-primary/5 ring-primary/25" : "bg-muted/40 ring-transparent",
                )}
              >
                <div className="flex min-w-0 items-center gap-2">
                  <div className="flex shrink-0 flex-col gap-0.5">
                    <button
                      type="button"
                      aria-label="بالا در منو"
                      className="grid h-6 w-6 place-items-center rounded bg-card disabled:opacity-30"
                      disabled={idx === 0}
                      onClick={() => store.moveDockOrb(orb.key, -1)}
                    >
                      <ArrowUp size={12} set="light" primaryColor="#5E5F5E" />
                    </button>
                    <button
                      type="button"
                      aria-label="پایین در منو"
                      className="grid h-6 w-6 place-items-center rounded bg-card disabled:opacity-30"
                      disabled={idx === dock.categories.length - 1}
                      onClick={() => store.moveDockOrb(orb.key, 1)}
                    >
                      <ArrowDown size={12} set="light" primaryColor="#5E5F5E" />
                    </button>
                  </div>
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-white shadow-soft">
                    <DockIconPreview name={orb.icon} label={orb.name} />
                  </span>
                  <input
                    className="h-9 min-w-0 flex-1 rounded-xl bg-card px-3 text-sm font-bold outline-none"
                    value={orb.name}
                    onChange={(e) => store.updateOrb(orb.key, { name: e.target.value })}
                  />
                  <button
                    type="button"
                    className={cn(
                      "shrink-0 rounded-lg px-2.5 py-2 text-[10px] font-bold",
                      isFeatured
                        ? "bg-primary text-primary-foreground"
                        : "bg-card text-ink disabled:opacity-40",
                    )}
                    disabled={!isFeatured && featured.length >= 6}
                    onClick={() => {
                      if (isFeatured) {
                        store.setOrbFeaturedOrder(orb.key, null);
                        toast.message(`«${orb.name}» از داک هیرو برداشته شد`);
                      } else {
                        addToHeroDock(orb.key);
                      }
                    }}
                  >
                    {isFeatured ? `پاور ${orb.featuredOrder! + 1}` : "افزودن به داک هیرو"}
                  </button>
                  <button
                    type="button"
                    aria-label="حذف از منو"
                    className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-card"
                    onClick={() => {
                      store.removeOrbFromDock(orb.key);
                      toast.message(`«${orb.name}» از منو حذف شد`);
                    }}
                  >
                    <Delete size={14} set="light" primaryColor="#D02327" />
                  </button>
                </div>

                {isFeatured ? (
                  <div className="flex flex-wrap gap-1.5">
                    {SLOT_INDEXES.map((slot) => (
                      <button
                        key={slot}
                        type="button"
                        onClick={() => store.assignFeaturedSlot(orb.key, slot)}
                        className={cn(
                          "h-7 w-7 rounded-lg text-[10px] font-black",
                          orb.featuredOrder === slot
                            ? "bg-primary text-white"
                            : "bg-card text-ink shadow-soft",
                        )}
                      >
                        {slot + 1}
                      </button>
                    ))}
                  </div>
                ) : null}

                <div className="grid grid-cols-2 gap-2">
                  <label className="text-[10px] font-bold text-muted-foreground">
                    آیکون (URL یا Iconly)
                    <input
                      dir="ltr"
                      className="mt-1 h-9 w-full rounded-xl bg-card px-2 text-xs font-bold shadow-soft"
                      value={orb.icon}
                      onChange={(e) => store.updateOrb(orb.key, { icon: e.target.value })}
                      list={`dock-icon-options-${orb.key}`}
                      placeholder="/category-icons/..."
                    />
                    <datalist id={`dock-icon-options-${orb.key}`}>
                      {ICON_OPTIONS.map((icon) => (
                        <option key={icon} value={icon} />
                      ))}
                    </datalist>
                  </label>
                  <label className="text-[10px] font-bold text-muted-foreground">
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
                <textarea
                  className="min-h-[52px] w-full min-w-0 rounded-xl bg-card px-3 py-2 text-[11px] leading-relaxed outline-none"
                  value={orb.subtitle}
                  onChange={(e) => store.updateOrb(orb.key, { subtitle: e.target.value })}
                />
                <input
                  dir="ltr"
                  className="h-9 w-full min-w-0 rounded-xl bg-card px-3 text-xs outline-none"
                  value={orb.heroImage}
                  onChange={(e) => store.updateOrb(orb.key, { heroImage: e.target.value })}
                  placeholder="/images/hero/..."
                />
              </div>
            );
          })}
          {!dock.categories.length ? (
            <p className="text-xs text-muted-foreground">
              منو خالی است — از ستون «قابل افزودن» یا دکمه همگام‌سازی استفاده کنید.
            </p>
          ) : null}
        </section>

        {/* Available L1 to add */}
        <section className="space-y-3 rounded-2xl bg-card p-4 shadow-soft">
          <h2 className="text-sm font-black text-ink">قابل افزودن از L1</h2>
          <p className="text-[11px] text-muted-foreground">
            دسته‌های لایه اول دیتابیس که هنوز در منو نیستند
          </p>
          {availableToAdd.map((root) => (
            <div
              key={root.id}
              className="flex items-center gap-2 rounded-xl bg-muted/50 px-3 py-2.5"
            >
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-bold">{root.name}</div>
                <div className="text-[10px] text-muted-foreground" dir="ltr">
                  id:{root.id}
                  {root.slug ? ` · ${root.slug}` : ""}
                </div>
              </div>
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
                افزودن به منو
              </Button>
            </div>
          ))}
          {!availableToAdd.length && !categoriesLoading ? (
            <p className="rounded-xl bg-muted/60 px-3 py-2 text-xs text-muted-foreground">
              همهٔ دسته‌های L1 در منو هستند — یا دیتابیس هنوز لود نشده.
            </p>
          ) : null}
        </section>
      </div>
    </div>
  );
}
