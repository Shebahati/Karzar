"use client";

import { useEffect, useState } from "react";
import { Category } from "react-iconly";

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
import type { CategoryCreatePayload, CategoryFlat, CategoryUpdatePayload } from "@/types/category";

export type CategoryFormValues = {
  name: string;
  slug?: string;
  icon?: string;
  meta_title?: string;
  meta_description?: string;
  spec_template_key?: string;
};

interface CategoryFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: "create" | "edit";
  layerLabel: string;
  parentId?: number | null;
  category?: CategoryFlat | null;
  onSubmit: (values: CategoryFormValues) => Promise<void>;
  pending?: boolean;
}

export function CategoryFormDialog({
  open,
  onOpenChange,
  mode,
  layerLabel,
  parentId,
  category,
  onSubmit,
  pending,
}: CategoryFormDialogProps) {
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [icon, setIcon] = useState("");
  const [metaTitle, setMetaTitle] = useState("");
  const [metaDescription, setMetaDescription] = useState("");
  const [specKey, setSpecKey] = useState("");

  useEffect(() => {
    if (open) {
      setName(category?.name ?? "");
      setSlug(category?.slug ?? "");
      setIcon(category?.icon ?? "");
      setMetaTitle(category?.meta_title ?? "");
      setMetaDescription(category?.meta_description ?? "");
      setSpecKey(category?.spec_template_key ?? "");
    }
  }, [open, category]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    await onSubmit({
      name: trimmed,
      slug: mode === "edit" ? slug.trim() || undefined : undefined,
      icon: icon.trim() || undefined,
      meta_title: metaTitle.trim() || undefined,
      meta_description: metaDescription.trim() || undefined,
      spec_template_key: specKey.trim() || undefined,
    });
  }

  return (
    <Dialog open={open} onOpenChange={(next) => (!pending ? onOpenChange(next) : undefined)}>
      <DialogContent className="max-w-lg border-transparent shadow-card">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-accent text-primary">
          <Category set="bulk" size={24} primaryColor="#C22026" />
        </div>
        <DialogHeader>
          <DialogTitle className="text-[#4F4F4F]">
            {mode === "create" ? `افزودن ${layerLabel}` : `ویرایش ${layerLabel}`}
          </DialogTitle>
          <DialogDescription>
            {mode === "create" && parentId
              ? `زیرمجموعه والد با شناسه ${parentId}`
              : category?.breadcrumb.join(" / ")}
            {category ? ` · عمق ${category.depth}` : ""}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex max-h-[70vh] flex-col gap-4 overflow-y-auto">
          <Field label="نام دسته‌بندی" htmlFor="category-name" required>
            <Input
              id="category-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
              disabled={pending}
            />
          </Field>
          {mode === "edit" && (
            <Field label="اسلاگ (slug)" htmlFor="category-slug">
              <Input
                id="category-slug"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                dir="ltr"
                disabled={pending}
              />
            </Field>
          )}
          <Field label="آیکون (react-iconly)" htmlFor="category-icon">
            <Input
              id="category-icon"
              value={icon}
              onChange={(e) => setIcon(e.target.value)}
              placeholder="Category"
              dir="ltr"
              disabled={pending}
            />
          </Field>
          <Field label="کلید قالب مشخصات" htmlFor="category-spec-key">
            <Input
              id="category-spec-key"
              value={specKey}
              onChange={(e) => setSpecKey(e.target.value)}
              placeholder="measurement"
              dir="ltr"
              disabled={pending}
            />
          </Field>
          <Field label="Meta title" htmlFor="category-meta-title">
            <Input
              id="category-meta-title"
              value={metaTitle}
              onChange={(e) => setMetaTitle(e.target.value)}
              disabled={pending}
            />
          </Field>
          <Field label="Meta description" htmlFor="category-meta-description">
            <Input
              id="category-meta-description"
              value={metaDescription}
              onChange={(e) => setMetaDescription(e.target.value)}
              disabled={pending}
            />
          </Field>
          <div className="flex gap-3">
            <Button type="submit" className="flex-1" disabled={pending}>
              {pending ? "در حال ذخیره..." : "ذخیره"}
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

export function toCreatePayload(
  values: CategoryFormValues,
  parentId: number | null | undefined,
): CategoryCreatePayload {
  return {
    name: values.name,
    parent_id: parentId ?? null,
    icon: values.icon,
    meta_title: values.meta_title,
    meta_description: values.meta_description,
    spec_template_key: values.spec_template_key,
  };
}

export function toUpdatePayload(values: CategoryFormValues): CategoryUpdatePayload {
  return {
    name: values.name,
    slug: values.slug,
    icon: values.icon ?? null,
    meta_title: values.meta_title ?? null,
    meta_description: values.meta_description ?? null,
    spec_template_key: values.spec_template_key ?? null,
  };
}
