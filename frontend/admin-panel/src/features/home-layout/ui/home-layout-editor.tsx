"use client";

import { useEffect, useMemo, useState } from "react";
import { ArrowDown, ArrowUp, Delete, Plus } from "react-iconly";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import {
  BUILTIN_SECTION_LABELS,
  createCategoryCarouselSection,
  createDefaultHomeLayoutPack,
  validateHomeLayoutPack,
  type CategoryCarouselSection,
  type HomeLayoutPack,
  type HomeLayoutSection,
} from "@/entities/home-layout";
import { useFlatCategories } from "@/features/catalog/queries";
import {
  loadHomeLayoutPack,
  publishHomeLayoutPack,
} from "@/features/home-layout/lib/publish-home-layout";
import type { CategoryFlat } from "@/types/category";
import { cn } from "@/lib/utils";

function sectionLabel(section: HomeLayoutSection): string {
  if (section.type === "category_carousel") {
    return section.title.trim() || "کروسل دسته (بدون عنوان)";
  }
  return BUILTIN_SECTION_LABELS[section.type];
}

function isCarousel(
  section: HomeLayoutSection,
): section is CategoryCarouselSection {
  return section.type === "category_carousel";
}

export function HomeLayoutEditor() {
  const { data: flatCategories = [], isPending: catsPending } =
    useFlatCategories();

  const selectableCategories = useMemo(() => {
    return (flatCategories as CategoryFlat[])
      .filter((c) => c.is_selectable !== false)
      .sort((a, b) => {
        const ba = (a.breadcrumb ?? []).join(" / ");
        const bb = (b.breadcrumb ?? []).join(" / ");
        return ba.localeCompare(bb, "fa") || a.name.localeCompare(b.name, "fa");
      });
  }, [flatCategories]);

  const [pack, setPack] = useState<HomeLayoutPack | null>(null);
  const [loading, setLoading] = useState(true);
  const [publishing, setPublishing] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const loaded = await loadHomeLayoutPack();
        if (!cancelled) {
          setPack(loaded);
          setDirty(false);
        }
      } catch {
        if (!cancelled) {
          setPack(createDefaultHomeLayoutPack());
          toast.error("بارگذاری چیدمان هوم ناموفق بود — پیش‌فرض بارگذاری شد");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const sections = pack?.sections ?? [];

  function updateSections(
    updater: (prev: HomeLayoutSection[]) => HomeLayoutSection[],
  ) {
    setPack((prev) => {
      const base = prev ?? createDefaultHomeLayoutPack();
      return { ...base, sections: updater(base.sections) };
    });
    setDirty(true);
  }

  function moveSection(id: string, direction: -1 | 1) {
    updateSections((prev) => {
      const idx = prev.findIndex((s) => s.id === id);
      const next = idx + direction;
      if (idx < 0 || next < 0 || next >= prev.length) return prev;
      const copy = [...prev];
      const [item] = copy.splice(idx, 1);
      copy.splice(next, 0, item);
      return copy;
    });
  }

  function toggleEnabled(id: string, enabled: boolean) {
    updateSections((prev) =>
      prev.map((s) => (s.id === id ? { ...s, enabled } : s)),
    );
  }

  function patchCarousel(
    id: string,
    patch: Partial<Omit<CategoryCarouselSection, "id" | "type">>,
  ) {
    updateSections((prev) =>
      prev.map((s) =>
        s.id === id && isCarousel(s) ? { ...s, ...patch } : s,
      ),
    );
  }

  function addCarousel() {
    const section = createCategoryCarouselSection({
      title: "کروسل جدید",
      subtitle: "",
      ctaLabel: "مشاهده همه",
    });
    updateSections((prev) => [...prev, section]);
    setExpandedId(section.id);
  }

  function removeCarousel(id: string) {
    updateSections((prev) => prev.filter((s) => s.id !== id));
    if (expandedId === id) setExpandedId(null);
  }

  async function handlePublish() {
    if (!pack) return;
    const issues = validateHomeLayoutPack(pack);
    if (issues.length) {
      toast.error(issues[0]?.message ?? "چیدمان نامعتبر است");
      const first = issues[0]?.sectionId;
      if (first) setExpandedId(first);
      return;
    }

    setPublishing(true);
    try {
      const result = await publishHomeLayoutPack(pack);
      if (!result.fileOk) {
        toast.error(result.detail ?? "انتشار ناموفق بود");
        return;
      }
      if (result.pack) setPack(result.pack);
      setDirty(false);
      toast.success("چیدمان صفحه هوم منتشر شد");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "خطا در انتشار");
    } finally {
      setPublishing(false);
    }
  }

  if (loading || !pack) {
    return (
      <div className="mx-auto flex max-w-3xl flex-col gap-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-[#4F4F4F]">مدیریت صفحه هوم</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            ترتیب و نمایش بخش‌های زیر هیرو را تنظیم کنید. هیرو از «طراحی هیرو»
            مدیریت می‌شود.
          </p>
          {pack.publishedAt ? (
            <p className="mt-1 text-xs text-muted-foreground">
              آخرین انتشار:{" "}
              {new Date(pack.publishedAt).toLocaleString("fa-IR")}
              {dirty ? " · تغییرات ذخیره نشده" : ""}
            </p>
          ) : (
            <p className="mt-1 text-xs text-muted-foreground">
              هنوز منتشر نشده — پیش‌فرض فعلی فروشگاه
            </p>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={addCarousel}
          >
            <Plus set="light" size={16} />
            افزودن کروسل دسته
          </Button>
          <Button
            type="button"
            size="sm"
            className="bg-[#D02327] hover:bg-[#B01E22]"
            disabled={publishing}
            onClick={() => void handlePublish()}
          >
            {publishing ? "در حال انتشار…" : "انتشار"}
          </Button>
        </div>
      </div>

      <Card className="border-transparent shadow-sm">
        <CardContent className="divide-y divide-gray-100 p-0">
          {sections.map((section, index) => {
            const carousel = isCarousel(section);
            const expanded = expandedId === section.id;
            return (
              <div
                key={section.id}
                className={cn(
                  "px-4 py-4 transition-colors",
                  !section.enabled && "bg-muted/30 opacity-80",
                )}
              >
                <div className="flex flex-wrap items-center gap-3">
                  <span className="w-6 text-center text-xs tabular-nums text-muted-foreground">
                    {index + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-bold text-[#4F4F4F]">
                        {sectionLabel(section)}
                      </span>
                      <Badge variant="outline" className="text-[10px]">
                        {carousel ? "کروسل دسته" : "بخش ثابت"}
                      </Badge>
                    </div>
                    {carousel && section.categorySlug ? (
                      <p className="mt-0.5 text-xs text-muted-foreground" dir="ltr">
                        {section.categorySlug}
                        {section.categoryId > 0 ? ` · #${section.categoryId}` : ""}
                      </p>
                    ) : null}
                  </div>

                  <div className="flex items-center gap-1">
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      disabled={index === 0}
                      aria-label="جابجایی به بالا"
                      onClick={() => moveSection(section.id, -1)}
                    >
                      <ArrowUp set="light" size={16} />
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      disabled={index === sections.length - 1}
                      aria-label="جابجایی به پایین"
                      onClick={() => moveSection(section.id, 1)}
                    >
                      <ArrowDown set="light" size={16} />
                    </Button>
                  </div>

                  <Switch
                    checked={section.enabled}
                    onCheckedChange={(v) => toggleEnabled(section.id, v)}
                    aria-label="فعال"
                  />

                  {carousel ? (
                    <>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          setExpandedId(expanded ? null : section.id)
                        }
                      >
                        {expanded ? "بستن" : "ویرایش"}
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-destructive"
                        aria-label="حذف کروسل"
                        onClick={() => removeCarousel(section.id)}
                      >
                        <Delete set="light" size={16} />
                      </Button>
                    </>
                  ) : null}
                </div>

                {carousel && expanded ? (
                  <div className="mt-4 grid gap-3 rounded-lg border border-border/60 bg-white p-4 sm:grid-cols-2">
                    <div className="space-y-1.5 sm:col-span-2">
                      <Label htmlFor={`title-${section.id}`}>عنوان</Label>
                      <Input
                        id={`title-${section.id}`}
                        value={section.title}
                        onChange={(e) =>
                          patchCarousel(section.id, { title: e.target.value })
                        }
                        placeholder="مثلاً اندازه‌گیری"
                      />
                    </div>
                    <div className="space-y-1.5 sm:col-span-2">
                      <Label htmlFor={`sub-${section.id}`}>
                        زیر‌عنوان (اختیاری)
                      </Label>
                      <Textarea
                        id={`sub-${section.id}`}
                        rows={2}
                        value={section.subtitle ?? ""}
                        onChange={(e) =>
                          patchCarousel(section.id, {
                            subtitle: e.target.value,
                          })
                        }
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor={`cta-${section.id}`}>
                        متن لینک (اختیاری)
                      </Label>
                      <Input
                        id={`cta-${section.id}`}
                        value={section.ctaLabel ?? ""}
                        onChange={(e) =>
                          patchCarousel(section.id, {
                            ctaLabel: e.target.value,
                          })
                        }
                        placeholder="مشاهده همه"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor={`limit-${section.id}`}>تعداد محصول</Label>
                      <Input
                        id={`limit-${section.id}`}
                        type="number"
                        min={4}
                        max={48}
                        value={section.limit ?? 12}
                        onChange={(e) =>
                          patchCarousel(section.id, {
                            limit: Number(e.target.value) || 12,
                          })
                        }
                      />
                    </div>
                    <div className="space-y-1.5 sm:col-span-2">
                      <Label htmlFor={`cat-${section.id}`}>دسته</Label>
                      <select
                        id={`cat-${section.id}`}
                        className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                        disabled={catsPending}
                        value={
                          section.categoryId > 0
                            ? String(section.categoryId)
                            : ""
                        }
                        onChange={(e) => {
                          const id = Number(e.target.value);
                          const cat = selectableCategories.find(
                            (c) => c.id === id,
                          );
                          patchCarousel(section.id, {
                            categoryId: id || 0,
                            categorySlug: cat?.slug,
                            title:
                              section.title.trim() ||
                              cat?.name ||
                              section.title,
                          });
                        }}
                      >
                        <option value="">
                          {catsPending
                            ? "در حال بارگذاری…"
                            : section.categorySlug && !(section.categoryId > 0)
                              ? `پیش‌فرض اسلاگ: ${section.categorySlug}`
                              : "انتخاب دسته…"}
                        </option>
                        {selectableCategories.map((cat) => {
                          const label =
                            cat.breadcrumb?.length > 0
                              ? cat.breadcrumb.join(" / ")
                              : cat.name;
                          const indent = "— ".repeat(
                            Math.max(0, (cat.depth ?? 1) - 1),
                          );
                          return (
                            <option key={cat.id} value={cat.id}>
                              {indent}
                              {label}
                            </option>
                          );
                        })}
                      </select>
                      {section.categorySlug && !(section.categoryId > 0) ? (
                        <p className="text-xs text-muted-foreground">
                          تا انتخاب دستی، فروشگاه با اسلاگ{" "}
                          <span dir="ltr">{section.categorySlug}</span> دسته را
                          پیدا می‌کند.
                        </p>
                      ) : null}
                    </div>
                  </div>
                ) : null}
              </div>
            );
          })}
        </CardContent>
      </Card>

      <p className="text-xs leading-relaxed text-muted-foreground">
        بخش‌های ثابت (پرتخفیف، پرفروش، ویژگی‌ها، …) فقط جابجا یا خاموش می‌شوند.
        کروسل دسته همان استایل کروسل‌های فعلی هوم را با محصولات همان دسته نشان
        می‌دهد.
      </p>
    </div>
  );
}
