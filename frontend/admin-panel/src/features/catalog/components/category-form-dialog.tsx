"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import { Category, Upload } from "react-iconly";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { useUploadCategoryImage, useUpdateCategory } from "@/features/catalog/queries";
import { ApiError } from "@/lib/api-client";
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
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [iconPreviewUrl, setIconPreviewUrl] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const iconFileRef = useRef<HTMLInputElement>(null);
  const uploadImage = useUploadCategoryImage();
  const updateCategory = useUpdateCategory();

  useEffect(() => {
    if (open) {
      setName(category?.name ?? "");
      setSlug(category?.slug ?? "");
      setIcon(category?.icon ?? "");
      setMetaTitle(category?.meta_title ?? "");
      setMetaDescription(category?.meta_description ?? "");
      setSpecKey(category?.spec_template_key ?? "");
      setPreviewUrl(category?.image_url ?? null);
      setIconPreviewUrl(
        category?.icon &&
          (category.icon.startsWith("/") ||
            category.icon.startsWith("http") ||
            category.icon.startsWith("blob:"))
          ? category.icon
          : null,
      );
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

  async function handleImagePick(file: File | undefined) {
    if (!file || !category) return;
    try {
      const result = await uploadImage.mutateAsync({ id: category.id, file });
      setPreviewUrl(result.image_url);
      toast.success("تصویر دسته آپلود شد");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "آپلود تصویر ناموفق بود");
    }
  }

  async function handleIconPick(file: File | undefined) {
    if (!file || !category) return;
    try {
      const result = await uploadImage.mutateAsync({ id: category.id, file });
      const url = result.image_url;
      await updateCategory.mutateAsync({
        id: category.id,
        payload: { icon: url },
      });
      setIcon(url);
      setIconPreviewUrl(url);
      toast.success("آیکون دسته ذخیره شد");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "آپلود آیکون ناموفق بود");
    }
  }

  return (
    <Sheet open={open} onOpenChange={(next) => (!pending ? onOpenChange(next) : undefined)}>
      <SheetContent side="left" className="p-0">
        <SheetHeader className="pe-14">
          <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-accent text-primary">
            <Category set="bulk" size={24} primaryColor="#D02327" />
          </div>
          <SheetTitle className="text-[#4F4F4F]">
            {mode === "create" ? `افزودن ${layerLabel}` : `ویرایش ${layerLabel}`}
          </SheetTitle>
          <SheetDescription>
            {mode === "create" && parentId
              ? `زیرمجموعه والد با شناسه ${parentId}`
              : category?.breadcrumb.join(" / ")}
            {category ? ` · عمق ${category.depth}` : ""}
          </SheetDescription>
        </SheetHeader>

        <form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
          <div className="flex-1 space-y-4 overflow-y-auto px-7 pb-4">
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
            {mode === "edit" && category && (
              <Field label="تصویر کارت (فروشگاه)" htmlFor="category-image">
                <div className="flex items-center gap-3">
                  <span className="relative block h-16 w-16 shrink-0 overflow-hidden rounded-xl bg-[#F7F7F7] ring-1 ring-border/40">
                    {previewUrl ? (
                      <Image
                        src={previewUrl}
                        alt=""
                        width={64}
                        height={64}
                        className="h-full w-full object-cover"
                        unoptimized={previewUrl.toLowerCase().includes(".svg")}
                      />
                    ) : (
                      <span className="grid h-full w-full place-items-center text-xs text-muted-foreground">
                        بدون تصویر
                      </span>
                    )}
                  </span>
                  <div className="flex flex-col gap-2">
                    <input
                      ref={fileRef}
                      id="category-image"
                      type="file"
                      accept="image/png,image/jpeg,image/webp,image/gif,image/svg+xml"
                      className="hidden"
                      onChange={(e) => {
                        void handleImagePick(e.target.files?.[0]);
                        e.target.value = "";
                      }}
                    />
                    <Button
                      type="button"
                      variant="outline"
                      disabled={uploadImage.isPending || pending}
                      onClick={() => fileRef.current?.click()}
                    >
                      <Upload set="light" size={16} primaryColor="currentColor" />
                      {uploadImage.isPending ? "در حال آپلود..." : "آپلود تصویر"}
                    </Button>
                  </div>
                </div>
              </Field>
            )}

            {mode === "edit" && category && (
              <Field label="آیکون داک / اورب (PNG)" htmlFor="category-icon-file">
                <div className="flex items-center gap-3">
                  <span className="relative grid h-16 w-16 shrink-0 place-items-center overflow-hidden rounded-full bg-[#F7F7F7] ring-1 ring-border/40">
                    {iconPreviewUrl ? (
                      <Image
                        src={iconPreviewUrl}
                        alt=""
                        width={56}
                        height={56}
                        className="h-14 w-14 object-contain"
                        unoptimized
                      />
                    ) : (
                      <span className="text-[10px] text-muted-foreground">بدون آیکون</span>
                    )}
                  </span>
                  <div className="flex flex-col gap-2">
                    <input
                      ref={iconFileRef}
                      id="category-icon-file"
                      type="file"
                      accept="image/png,image/jpeg,image/webp,image/gif,image/svg+xml"
                      className="hidden"
                      onChange={(e) => {
                        void handleIconPick(e.target.files?.[0]);
                        e.target.value = "";
                      }}
                    />
                    <Button
                      type="button"
                      variant="outline"
                      disabled={uploadImage.isPending || updateCategory.isPending || pending}
                      onClick={() => iconFileRef.current?.click()}
                    >
                      <Upload set="light" size={16} primaryColor="currentColor" />
                      {uploadImage.isPending || updateCategory.isPending
                        ? "در حال آپلود..."
                        : "آپلود آیکون"}
                    </Button>
                    <p className="text-[11px] text-muted-foreground">
                      روی داک هیرو و کاروسل فروشگاه نمایش داده می‌شود
                    </p>
                  </div>
                </div>
              </Field>
            )}

            <Field label="آیکون (URL یا نام Iconly)" htmlFor="category-icon">
              <Input
                id="category-icon"
                value={icon}
                onChange={(e) => {
                  setIcon(e.target.value);
                  const v = e.target.value.trim();
                  setIconPreviewUrl(
                    v.startsWith("/") || v.startsWith("http") || v.startsWith("blob:")
                      ? v
                      : null,
                  );
                }}
                placeholder="/category-icons/andaze-giri.png"
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
          </div>

          <SheetFooter>
            <Button type="submit" className="flex-1" disabled={pending}>
              {pending ? "در حال ذخیره..." : "ذخیره"}
            </Button>
            <Button type="button" variant="ghost" disabled={pending} onClick={() => onOpenChange(false)}>
              انصراف
            </Button>
          </SheetFooter>
        </form>
      </SheetContent>
    </Sheet>
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
