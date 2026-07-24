"use client";

import { useEffect, useState } from "react";
import { Image2 } from "react-iconly";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import type { HeroSlide, HeroSlideCreatePayload } from "@/types/cms";

interface HeroSlideFormValues {
  title: string;
  subtitle: string;
  cta_label: string;
  cta_href: string;
  image: string;
  accent: string;
  sort_order: string;
  is_active: boolean;
}

function emptyValues(nextSortOrder: number): HeroSlideFormValues {
  return {
    title: "",
    subtitle: "",
    cta_label: "",
    cta_href: "",
    image: "",
    accent: "#C22026",
    sort_order: String(nextSortOrder),
    is_active: true,
  };
}

function valuesFromSlide(slide: HeroSlide): HeroSlideFormValues {
  return {
    title: slide.title,
    subtitle: slide.subtitle ?? "",
    cta_label: slide.cta_label ?? "",
    cta_href: slide.cta_href ?? "",
    image: slide.image,
    accent: slide.accent,
    sort_order: String(slide.sort_order),
    is_active: slide.is_active,
  };
}

interface HeroSlideFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: "create" | "edit";
  slide?: HeroSlide | null;
  nextSortOrder: number;
  onSubmit: (payload: HeroSlideCreatePayload) => Promise<void>;
  pending?: boolean;
}

export function HeroSlideFormDialog({
  open,
  onOpenChange,
  mode,
  slide,
  nextSortOrder,
  onSubmit,
  pending,
}: HeroSlideFormDialogProps) {
  const [values, setValues] = useState<HeroSlideFormValues>(emptyValues(nextSortOrder));
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (open) {
      setValues(slide ? valuesFromSlide(slide) : emptyValues(nextSortOrder));
      setErrors({});
    }
  }, [open, slide, nextSortOrder]);

  function update<K extends keyof HeroSlideFormValues>(key: K, value: HeroSlideFormValues[K]) {
    setValues((prev) => ({ ...prev, [key]: value }));
  }

  function validate(): boolean {
    const nextErrors: Record<string, string> = {};
    if (!values.title.trim()) nextErrors.title = "عنوان اسلاید الزامی است.";
    if (!values.image.trim()) nextErrors.image = "آدرس تصویر الزامی است.";
    if (!values.accent.trim()) nextErrors.accent = "رنگ اصلی الزامی است.";
    const order = Number(values.sort_order);
    if (!values.sort_order.trim() || Number.isNaN(order)) {
      nextErrors.sort_order = "ترتیب نمایش باید عددی باشد.";
    }
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    await onSubmit({
      title: values.title.trim(),
      subtitle: values.subtitle.trim() || null,
      cta_label: values.cta_label.trim() || null,
      cta_href: values.cta_href.trim() || null,
      image: values.image.trim(),
      accent: values.accent.trim(),
      sort_order: Number(values.sort_order),
      is_active: values.is_active,
    });
  }

  return (
    <Dialog open={open} onOpenChange={(next) => (!pending ? onOpenChange(next) : undefined)}>
      <DialogContent className="max-h-[90vh] max-w-lg overflow-y-auto border-transparent shadow-card">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-accent text-primary">
          <Image2 set="bulk" size={24} primaryColor="#C22026" />
        </div>
        <DialogHeader>
          <DialogTitle className="text-[#4F4F4F]">
            {mode === "create" ? "افزودن اسلاید هدر" : "ویرایش اسلاید هدر"}
          </DialogTitle>
          <DialogDescription>اسلایدهای بنر اصلی صفحه نخست فروشگاه را مدیریت کنید.</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <Field label="عنوان" htmlFor="hero-title" required error={errors.title}>
            <Input
              id="hero-title"
              value={values.title}
              onChange={(e) => update("title", e.target.value)}
              disabled={pending}
              aria-invalid={Boolean(errors.title)}
              autoFocus
            />
          </Field>

          <Field label="زیرعنوان" htmlFor="hero-subtitle" hint="اختیاری">
            <Input
              id="hero-subtitle"
              value={values.subtitle}
              onChange={(e) => update("subtitle", e.target.value)}
              disabled={pending}
            />
          </Field>

          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
            <Field label="متن دکمه" htmlFor="hero-cta-label" hint="اختیاری">
              <Input
                id="hero-cta-label"
                value={values.cta_label}
                onChange={(e) => update("cta_label", e.target.value)}
                disabled={pending}
              />
            </Field>
            <Field label="لینک دکمه" htmlFor="hero-cta-href" hint="اختیاری">
              <Input
                id="hero-cta-href"
                dir="ltr"
                className="text-start"
                value={values.cta_href}
                onChange={(e) => update("cta_href", e.target.value)}
                disabled={pending}
                placeholder="/products?category=1"
              />
            </Field>
          </div>

          <Field label="آدرس تصویر" htmlFor="hero-image" required error={errors.image}>
            <Input
              id="hero-image"
              dir="ltr"
              className="text-start"
              value={values.image}
              onChange={(e) => update("image", e.target.value)}
              disabled={pending}
              aria-invalid={Boolean(errors.image)}
              placeholder="https://..."
            />
          </Field>

          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
            <Field label="رنگ اصلی" htmlFor="hero-accent" required error={errors.accent}>
              <div className="flex items-center gap-2">
                <span
                  className="h-11 w-11 shrink-0 rounded-lg shadow-soft"
                  style={{ backgroundColor: values.accent || "#C22026" }}
                />
                <Input
                  id="hero-accent"
                  dir="ltr"
                  className="text-start tnum"
                  value={values.accent}
                  onChange={(e) => update("accent", e.target.value)}
                  disabled={pending}
                  aria-invalid={Boolean(errors.accent)}
                  placeholder="#C22026"
                />
              </div>
            </Field>

            <Field label="ترتیب نمایش" htmlFor="hero-sort-order" required error={errors.sort_order}>
              <Input
                id="hero-sort-order"
                dir="ltr"
                inputMode="numeric"
                className="text-start tnum"
                value={values.sort_order}
                onChange={(e) => update("sort_order", e.target.value.replace(/[^\d]/g, ""))}
                disabled={pending}
                aria-invalid={Boolean(errors.sort_order)}
              />
            </Field>
          </div>

          <label className="flex cursor-pointer items-center justify-between gap-3 rounded-xl bg-[#F7F7F7] px-4 py-3 shadow-soft">
            <span className="flex flex-col">
              <span className="text-sm font-bold text-[#4F4F4F]">اسلاید فعال</span>
              <span className="text-xs text-muted-foreground">نمایش در صفحه نخست فروشگاه</span>
            </span>
            <Switch
              checked={values.is_active}
              onCheckedChange={(checked) => update("is_active", checked)}
              disabled={pending}
            />
          </label>

          <div className="flex gap-3">
            <Button type="submit" className="flex-1" disabled={pending}>
              {pending ? "در حال ذخیره..." : "ذخیره اسلاید"}
            </Button>
            <Button type="button" variant="ghost" disabled={pending} onClick={() => onOpenChange(false)}>
              انصراف
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
