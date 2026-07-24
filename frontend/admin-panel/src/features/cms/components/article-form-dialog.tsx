"use client";

import { useEffect, useState } from "react";
import { Document } from "react-iconly";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { DateTimePicker } from "@/components/ui/datetime-picker";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { TagInput } from "@/components/ui/tag-input";
import { Textarea } from "@/components/ui/textarea";
import { ArticleBlocksEditor } from "@/features/cms/components/article-blocks-editor";
import { RelatedProductsPicker } from "@/features/cms/components/related-products-picker";
import type { Article, ArticleBlock, ArticleCreatePayload } from "@/types/cms";

interface ArticleFormValues {
  slug: string;
  title: string;
  excerpt: string;
  cover_image: string;
  published_at: string;
  reading_minutes: string;
  author: string;
  tags: string[];
  related_product_ids: number[];
  blocks: ArticleBlock[];
  is_published: boolean;
}

function slugify(input: string): string {
  return input
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9\u0600-\u06FF\s-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/-+/g, "-");
}

function emptyValues(): ArticleFormValues {
  return {
    slug: "",
    title: "",
    excerpt: "",
    cover_image: "",
    published_at: new Date().toISOString(),
    reading_minutes: "5",
    author: "",
    tags: [],
    related_product_ids: [],
    blocks: [{ type: "paragraph", text: "" }],
    is_published: false,
  };
}

function valuesFromArticle(article: Article): ArticleFormValues {
  return {
    slug: article.slug,
    title: article.title,
    excerpt: article.excerpt,
    cover_image: article.cover_image ?? "",
    published_at: article.published_at,
    reading_minutes: String(article.reading_minutes),
    author: article.author,
    tags: article.tags,
    related_product_ids: article.related_product_ids,
    blocks: article.blocks.length > 0 ? article.blocks : [{ type: "paragraph", text: "" }],
    is_published: article.is_published,
  };
}

interface ArticleFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: "create" | "edit";
  article?: Article | null;
  onSubmit: (payload: ArticleCreatePayload) => Promise<void>;
  pending?: boolean;
}

export function ArticleFormDialog({
  open,
  onOpenChange,
  mode,
  article,
  onSubmit,
  pending,
}: ArticleFormDialogProps) {
  const [values, setValues] = useState<ArticleFormValues>(emptyValues());
  const [slugTouched, setSlugTouched] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [blockErrors, setBlockErrors] = useState<Record<number, string>>({});

  useEffect(() => {
    if (open) {
      setValues(article ? valuesFromArticle(article) : emptyValues());
      setSlugTouched(Boolean(article));
      setErrors({});
      setBlockErrors({});
    }
  }, [open, article]);

  function update<K extends keyof ArticleFormValues>(key: K, value: ArticleFormValues[K]) {
    setValues((prev) => ({ ...prev, [key]: value }));
  }

  function handleTitleChange(title: string) {
    update("title", title);
    if (!slugTouched) {
      update("slug", slugify(title));
    }
  }

  function validate(): boolean {
    const nextErrors: Record<string, string> = {};
    const nextBlockErrors: Record<number, string> = {};

    if (!values.title.trim()) nextErrors.title = "عنوان مقاله الزامی است.";
    if (!values.slug.trim()) nextErrors.slug = "اسلاگ الزامی است.";
    else if (!/^[a-z0-9-]+$/.test(values.slug.trim())) {
      nextErrors.slug = "اسلاگ فقط می‌تواند شامل حروف انگلیسی کوچک، عدد و خط تیره باشد.";
    }
    if (!values.excerpt.trim()) nextErrors.excerpt = "خلاصه مقاله الزامی است.";
    if (!values.author.trim()) nextErrors.author = "نام نویسنده الزامی است.";
    const minutes = Number(values.reading_minutes);
    if (!values.reading_minutes.trim() || Number.isNaN(minutes) || minutes <= 0) {
      nextErrors.reading_minutes = "زمان مطالعه باید عددی بزرگ‌تر از صفر باشد.";
    }
    if (!values.published_at) nextErrors.published_at = "تاریخ انتشار الزامی است.";

    values.blocks.forEach((block, index) => {
      if (block.type === "list") {
        if (!block.items || block.items.length === 0) {
          nextBlockErrors[index] = "حداقل یک مورد برای لیست وارد کنید.";
        }
      } else if (!block.text?.trim()) {
        nextBlockErrors[index] = "متن این بلاک نمی‌تواند خالی باشد.";
      }
    });

    setErrors(nextErrors);
    setBlockErrors(nextBlockErrors);
    return Object.keys(nextErrors).length === 0 && Object.keys(nextBlockErrors).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    const payload: ArticleCreatePayload = {
      slug: values.slug.trim(),
      title: values.title.trim(),
      excerpt: values.excerpt.trim(),
      cover_image: values.cover_image.trim() || null,
      published_at: values.published_at,
      reading_minutes: Number(values.reading_minutes),
      author: values.author.trim(),
      tags: values.tags,
      related_product_ids: values.related_product_ids,
      blocks: values.blocks,
      is_published: values.is_published,
    };
    await onSubmit(payload);
  }

  return (
    <Dialog open={open} onOpenChange={(next) => (!pending ? onOpenChange(next) : undefined)}>
      <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto border-transparent shadow-card">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-accent text-primary">
          <Document set="bulk" size={24} primaryColor="#C22026" />
        </div>
        <DialogHeader>
          <DialogTitle className="text-[#4F4F4F]">
            {mode === "create" ? "افزودن مقاله جدید" : "ویرایش مقاله"}
          </DialogTitle>
          <DialogDescription>محتوای مقاله را برای نمایش در وبلاگ فروشگاه تکمیل کنید.</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <Field label="عنوان مقاله" htmlFor="article-title" required error={errors.title}>
            <Input
              id="article-title"
              value={values.title}
              onChange={(e) => handleTitleChange(e.target.value)}
              disabled={pending}
              aria-invalid={Boolean(errors.title)}
              autoFocus
            />
          </Field>

          <Field
            label="اسلاگ (آدرس URL)"
            htmlFor="article-slug"
            required
            error={errors.slug}
            hint="فقط حروف انگلیسی کوچک، عدد و خط تیره"
          >
            <Input
              id="article-slug"
              dir="ltr"
              className="text-start"
              value={values.slug}
              onChange={(e) => {
                setSlugTouched(true);
                update("slug", e.target.value);
              }}
              disabled={pending}
              aria-invalid={Boolean(errors.slug)}
            />
          </Field>

          <Field label="خلاصه مقاله" htmlFor="article-excerpt" required error={errors.excerpt}>
            <Textarea
              id="article-excerpt"
              rows={2}
              value={values.excerpt}
              onChange={(e) => update("excerpt", e.target.value)}
              disabled={pending}
              aria-invalid={Boolean(errors.excerpt)}
            />
          </Field>

          <Field
            label="تصویر کاور (آدرس)"
            htmlFor="article-cover"
            hint="اختیاری — آدرس URL تصویر شاخص"
          >
            <Input
              id="article-cover"
              dir="ltr"
              className="text-start"
              value={values.cover_image}
              onChange={(e) => update("cover_image", e.target.value)}
              disabled={pending}
              placeholder="https://..."
            />
          </Field>

          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
            <Field label="نویسنده" htmlFor="article-author" required error={errors.author}>
              <Input
                id="article-author"
                value={values.author}
                onChange={(e) => update("author", e.target.value)}
                disabled={pending}
                aria-invalid={Boolean(errors.author)}
              />
            </Field>

            <Field
              label="زمان مطالعه (دقیقه)"
              htmlFor="article-reading-minutes"
              required
              error={errors.reading_minutes}
            >
              <Input
                id="article-reading-minutes"
                dir="ltr"
                inputMode="numeric"
                className="text-start tnum"
                value={values.reading_minutes}
                onChange={(e) => update("reading_minutes", e.target.value.replace(/[^\d]/g, ""))}
                disabled={pending}
                aria-invalid={Boolean(errors.reading_minutes)}
              />
            </Field>
          </div>

          <Field label="تاریخ انتشار" required error={errors.published_at}>
            <DateTimePicker
              value={values.published_at}
              onChange={(iso) => update("published_at", iso)}
            />
          </Field>

          <Field label="برچسب‌ها" hint="اختیاری">
            <TagInput value={values.tags} onChange={(tags) => update("tags", tags)} disabled={pending} />
          </Field>

          <Field label="محصولات مرتبط" hint="اختیاری">
            <RelatedProductsPicker
              value={values.related_product_ids}
              onChange={(ids) => update("related_product_ids", ids)}
              disabled={pending}
            />
          </Field>

          <Field label="محتوای مقاله (بلاک‌ها)" required>
            <ArticleBlocksEditor
              blocks={values.blocks}
              onChange={(blocks) => update("blocks", blocks)}
              disabled={pending}
              errors={blockErrors}
            />
          </Field>

          <label className="flex cursor-pointer items-center justify-between gap-3 rounded-xl bg-[#F7F7F7] px-4 py-3 shadow-soft">
            <span className="flex flex-col">
              <span className="text-sm font-bold text-[#4F4F4F]">انتشار مقاله</span>
              <span className="text-xs text-muted-foreground">نمایش در وبلاگ فروشگاه</span>
            </span>
            <Switch
              checked={values.is_published}
              onCheckedChange={(checked) => update("is_published", checked)}
              disabled={pending}
            />
          </label>

          <div className="flex gap-3">
            <Button type="submit" className="flex-1" disabled={pending}>
              {pending ? "در حال ذخیره..." : "ذخیره مقاله"}
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
