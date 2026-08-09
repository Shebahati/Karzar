"use client";

import { useCallback, useRef, useState } from "react";
import Image from "next/image";
import { Image2, Paper, Plus, Upload } from "react-iconly";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Textarea } from "@/components/ui/textarea";
import {
  useProduct,
  useUploadProductImage,
} from "@/features/catalog/queries";
import { ApiError } from "@/lib/api-client";
import { cn } from "@/lib/utils";

const MAX_SIZE_BYTES = 5 * 1024 * 1024;
const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"];

/** Markdown image on its own line — Storefront PDP parses these as inline blocks. */
export function formatDescriptionImageMarkdown(src: string, alt = "تصویر محصول"): string {
  const safeAlt = alt.replace(/[[\]]/g, "").trim() || "تصویر محصول";
  const safeSrc = src.trim();
  return `![${safeAlt}](${safeSrc})`;
}

function insertAtCursor(
  value: string,
  insertion: string,
  start: number,
  end: number,
): { next: string; caret: number } {
  const before = value.slice(0, start);
  const after = value.slice(end);
  const lead =
    before.length === 0 || before.endsWith("\n\n")
      ? ""
      : before.endsWith("\n")
        ? "\n"
        : "\n\n";
  const trail =
    after.length === 0 || after.startsWith("\n\n")
      ? ""
      : after.startsWith("\n")
        ? "\n"
        : "\n\n";
  const block = `${lead}${insertion}${trail}`;
  return { next: `${before}${block}${after}`, caret: before.length + block.length };
}

function extractEmbeddedImages(value: string): Array<{ src: string; alt: string }> {
  const md = /!\[([^\]]*)\]\(([^)\s]+)\)/g;
  const html = /<img\b[^>]*\bsrc=["']([^"']+)["'][^>]*>/gi;
  const found: Array<{ src: string; alt: string }> = [];
  const seen = new Set<string>();

  for (const match of value.matchAll(md)) {
    const src = match[2]?.trim();
    if (!src || seen.has(src)) continue;
    seen.add(src);
    found.push({ src, alt: match[1]?.trim() || "تصویر محصول" });
  }
  for (const match of value.matchAll(html)) {
    const src = match[1]?.trim();
    if (!src || seen.has(src)) continue;
    seen.add(src);
    found.push({ src, alt: "تصویر محصول" });
  }
  return found;
}

export type ProductDescriptionEditorProps = {
  id?: string;
  value: string;
  onChange: (value: string) => void;
  onBlur?: () => void;
  disabled?: boolean;
  invalid?: boolean;
  /** When set, enables file upload + pick-from-gallery via product image APIs. */
  productId?: number;
  rows?: number;
  placeholder?: string;
};

export function ProductDescriptionEditor({
  id,
  value,
  onChange,
  onBlur,
  disabled,
  invalid,
  productId,
  rows = 8,
  placeholder = "توضیحات تکمیلی محصول — تصویر را از نوار بالا درج کنید",
}: ProductDescriptionEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  const [imageUrl, setImageUrl] = useState("");
  const [altText, setAltText] = useState("تصویر محصول");
  const [uploading, setUploading] = useState(false);

  const canUseProductMedia = typeof productId === "number" && productId > 0;
  const { data: product } = useProduct(productId ?? 0, canUseProductMedia);
  const upload = useUploadProductImage(canUseProductMedia ? productId! : 0);
  const gallery = product?.images ?? [];
  const embedded = extractEmbeddedImages(value);

  const applyInsert = useCallback(
    (src: string, alt?: string) => {
      const el = textareaRef.current;
      const start = el?.selectionStart ?? value.length;
      const end = el?.selectionEnd ?? value.length;
      const markdown = formatDescriptionImageMarkdown(src, alt ?? altText);
      const { next, caret } = insertAtCursor(value, markdown, start, end);
      onChange(next);
      setPanelOpen(false);
      setImageUrl("");
      requestAnimationFrame(() => {
        const node = textareaRef.current;
        if (!node) return;
        node.focus();
        node.setSelectionRange(caret, caret);
      });
    },
    [altText, onChange, value],
  );

  async function handleInsertUrl() {
    const url = imageUrl.trim();
    if (!url) return;
    try {
      // Validate absolute URL shape (http/https preferred; relative paths allowed for same-origin CDN).
      if (/^[a-z][a-z0-9+.-]*:/i.test(url) && !/^https?:\/\//i.test(url)) {
        toast.error("فقط لینک http یا https مجاز است");
        return;
      }
      applyInsert(url, altText);
      toast.success("تصویر در توضیحات درج شد");
    } catch {
      toast.error("درج تصویر ناموفق بود");
    }
  }

  async function handleUpload(file: File) {
    if (!canUseProductMedia) return;
    if (!ALLOWED_TYPES.includes(file.type)) {
      toast.error("فرمت تصویر نامعتبر است (JPG, PNG, WebP)");
      return;
    }
    if (file.size > MAX_SIZE_BYTES) {
      toast.error("حداکثر حجم ۵ مگابایت");
      return;
    }
    setUploading(true);
    try {
      const result = await upload.mutateAsync(file);
      applyInsert(result.url, altText);
      toast.success("تصویر آپلود و در توضیحات درج شد", {
        description: "این فایل به گالری محصول هم اضافه می‌شود.",
      });
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "آپلود ناموفق بود");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <Popover open={panelOpen} onOpenChange={setPanelOpen}>
          <PopoverTrigger asChild>
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={disabled}
              className="gap-2"
            >
              <Image2 set="light" size={16} primaryColor="currentColor" />
              درج تصویر
            </Button>
          </PopoverTrigger>
          <PopoverContent
            align="start"
            className="w-[min(100vw-2rem,22rem)] space-y-3 p-4"
            onOpenAutoFocus={(e) => e.preventDefault()}
          >
            <div>
              <p className="text-sm font-bold text-[#4F4F4F]">تصویر داخل توضیحات</p>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                در محل نشانگر متن درج می‌شود. متن فقط‌متنی قبلی بدون تغییر می‌ماند.
              </p>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground" htmlFor={`${id ?? "desc"}-img-alt`}>
                متن جایگزین (alt)
              </label>
              <Input
                id={`${id ?? "desc"}-img-alt`}
                value={altText}
                onChange={(e) => setAltText(e.target.value)}
                placeholder="توضیح کوتاه تصویر"
                disabled={disabled || uploading}
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground" htmlFor={`${id ?? "desc"}-img-url`}>
                لینک تصویر
              </label>
              <div className="flex gap-2">
                <Input
                  id={`${id ?? "desc"}-img-url`}
                  value={imageUrl}
                  onChange={(e) => setImageUrl(e.target.value)}
                  placeholder="https://..."
                  dir="ltr"
                  className="text-start"
                  disabled={disabled || uploading}
                />
                <Button
                  type="button"
                  size="sm"
                  className="shrink-0 gap-1.5"
                  disabled={disabled || uploading || !imageUrl.trim()}
                  onClick={() => void handleInsertUrl()}
                >
                  <Paper set="light" size={16} />
                  درج
                </Button>
              </div>
            </div>

            {canUseProductMedia ? (
              <>
                <input
                  ref={fileRef}
                  type="file"
                  accept={ALLOWED_TYPES.join(",")}
                  className="sr-only"
                  tabIndex={-1}
                  aria-hidden
                  disabled={disabled || uploading}
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) void handleUpload(file);
                  }}
                />
                <Button
                  type="button"
                  size="sm"
                  variant="secondary"
                  className="w-full gap-2"
                  disabled={disabled || uploading}
                  onClick={() => fileRef.current?.click()}
                >
                  <Upload set="light" size={16} primaryColor="currentColor" />
                  {uploading ? "در حال آپلود..." : "آپلود فایل و درج"}
                </Button>
                <p className="text-[11px] leading-relaxed text-muted-foreground">
                  آپلود از همان API گالری محصول استفاده می‌کند و تصویر به گالری هم افزوده
                  می‌شود. برای تصویر فقط‌توضیحات می‌توانید لینک مستقیم بگذارید.
                </p>

                {gallery.length > 0 ? (
                  <div className="space-y-2">
                    <p className="text-xs font-medium text-muted-foreground">
                      انتخاب از گالری
                    </p>
                    <div className="flex gap-2 overflow-x-auto pb-1">
                      {gallery.map((img) => (
                        <button
                          key={img.id}
                          type="button"
                          disabled={disabled || uploading}
                          onClick={() => {
                            applyInsert(img.url, altText);
                            toast.success("تصویر گالری در توضیحات درج شد");
                          }}
                          className="relative h-14 w-14 shrink-0 overflow-hidden rounded-lg border border-border bg-muted/30 transition hover:border-primary/50"
                          aria-label="درج از گالری"
                        >
                          <Image
                            src={img.url}
                            alt=""
                            fill
                            unoptimized={img.url.startsWith("blob:")}
                            className="object-contain p-0.5"
                            sizes="56px"
                          />
                        </button>
                      ))}
                    </div>
                  </div>
                ) : null}
              </>
            ) : (
              <p className="rounded-lg bg-muted/40 px-3 py-2 text-[11px] leading-relaxed text-muted-foreground">
                آپلود فایل پس از ذخیرهٔ اولیه محصول (صفحه ویرایش) فعال می‌شود. فعلاً لینک
                مستقیم وارد کنید.
              </p>
            )}
          </PopoverContent>
        </Popover>

        <span className="text-[11px] text-muted-foreground">
          تصویر بین پاراگراف‌ها به‌صورت بلاک نمایش داده می‌شود
        </span>
      </div>

      <Textarea
        ref={textareaRef}
        id={id}
        rows={rows}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onBlur={onBlur}
        disabled={disabled}
        placeholder={placeholder}
        aria-invalid={invalid || undefined}
        className={cn(
          "rounded-xl border border-input bg-white shadow-none",
          invalid && "ring-2 ring-destructive/50",
        )}
      />

      {embedded.length > 0 ? (
        <div className="flex flex-wrap items-center gap-2 rounded-xl bg-[#F7F7F7] px-3 py-2">
          <Plus set="light" size={14} primaryColor="#9E9E9E" />
          <span className="text-[11px] text-muted-foreground">
            {embedded.length} تصویر در متن:
          </span>
          {embedded.map((img) => (
            <span
              key={img.src}
              className="relative h-8 w-8 overflow-hidden rounded-md border border-border bg-white"
              title={img.alt}
            >
              {/* eslint-disable-next-line @next/next/no-img-element -- arbitrary description URLs */}
              <img src={img.src} alt="" className="h-full w-full object-contain" />
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}
