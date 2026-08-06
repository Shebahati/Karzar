"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Image from "next/image";
import { ArrowDown, ArrowUp, Delete, Image2, Paper, Plus } from "react-iconly";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  useAddProductImageByUrl,
  useDeleteProductImage,
  useProduct,
  useReorderProductImages,
  useSetPrimaryProductImage,
  useUploadProductImage,
} from "@/features/catalog/queries";
import { ApiError } from "@/lib/api-client";
import { cn, formatNumber, toPersianDigits } from "@/lib/utils";

const MAX_SIZE_BYTES = 5 * 1024 * 1024;
const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"];

type UploadProgress = { current: number; total: number } | null;

export function ProductImagesSection({ productId }: { productId: number }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const { data: product } = useProduct(productId);
  const upload = useUploadProductImage(productId);
  const addUrl = useAddProductImageByUrl(productId);
  const remove = useDeleteProductImage(productId);
  const setPrimary = useSetPrimaryProductImage(productId);
  const reorder = useReorderProductImages(productId);

  const [activeIndex, setActiveIndex] = useState(0);
  const [imageUrl, setImageUrl] = useState("");
  const [uploadProgress, setUploadProgress] = useState<UploadProgress>(null);

  const images = product?.images ?? [];
  const activeImage = images[activeIndex];
  const sortedIds = images.map((img) => img.id);
  const isUploading = uploadProgress !== null;

  useEffect(() => {
    if (activeIndex >= images.length) {
      setActiveIndex(Math.max(0, images.length - 1));
    }
  }, [images.length, activeIndex]);

  const validateFile = useCallback((file: File): string | null => {
    if (!ALLOWED_TYPES.includes(file.type)) {
      return "فرمت تصویر نامعتبر است (JPG, PNG, WebP)";
    }
    if (file.size > MAX_SIZE_BYTES) {
      return "حداکثر حجم ۵ مگابایت";
    }
    return null;
  }, []);

  const handleFiles = useCallback(
    async (fileList: FileList | File[]) => {
      const files = Array.from(fileList);
      if (files.length === 0 || isUploading) return;

      const valid: File[] = [];
      for (const file of files) {
        const error = validateFile(file);
        if (error) {
          toast.error(`${file.name}: ${error}`);
        } else {
          valid.push(file);
        }
      }
      if (valid.length === 0) return;

      let ok = 0;
      let fail = 0;
      const startIndex = images.length;
      setUploadProgress({ current: 0, total: valid.length });

      try {
        for (let i = 0; i < valid.length; i++) {
          setUploadProgress({ current: i + 1, total: valid.length });
          try {
            await upload.mutateAsync(valid[i]);
            ok += 1;
          } catch (err) {
            fail += 1;
            toast.error(
              err instanceof ApiError
                ? `${valid[i].name}: ${err.message}`
                : `آپلود «${valid[i].name}» ناموفق بود`,
            );
          }
        }

        if (ok > 0) {
          setActiveIndex(startIndex + ok - 1);
          if (fail === 0) {
            toast.success(
              ok === 1 ? "تصویر آپلود شد" : `${toPersianDigits(ok)} تصویر آپلود شد`,
            );
          } else {
            toast.warning(
              `${toPersianDigits(ok)} موفق، ${toPersianDigits(fail)} ناموفق`,
            );
          }
        }
      } finally {
        setUploadProgress(null);
        if (fileRef.current) fileRef.current.value = "";
      }
    },
    [images.length, isUploading, upload, validateFile],
  );

  async function handleAddUrl() {
    const url = imageUrl.trim();
    if (!url) return;
    try {
      await addUrl.mutateAsync(url);
      setImageUrl("");
      setActiveIndex(images.length);
      toast.success("تصویر از لینک اضافه شد");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "افزودن ناموفق بود");
    }
  }

  function moveImage(index: number, direction: -1 | 1) {
    const next = index + direction;
    if (next < 0 || next >= images.length) return;
    const ids = [...sortedIds];
    [ids[index], ids[next]] = [ids[next], ids[index]];
    reorder.mutate(ids, {
      onSuccess: () => {
        setActiveIndex(next);
        toast.success("ترتیب تصاویر به‌روز شد");
      },
      onError: (err) =>
        toast.error(err instanceof ApiError ? err.message : "مرتب‌سازی ناموفق بود"),
    });
  }

  function openFilePicker() {
    if (!isUploading) fileRef.current?.click();
  }

  return (
    <Card className="overflow-hidden border-primary/10">
      <CardHeader className="flex-row flex-wrap items-center justify-between gap-3 bg-gradient-to-l from-accent/40 to-card">
        <div>
          <CardTitle>گالری تصاویر</CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">
            کاور، آپلود فایل، لینک مستقیم، مرتب‌سازی
          </p>
        </div>
        <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-bold text-primary tnum">
          {formatNumber(images.length)} تصویر
        </span>
      </CardHeader>

      <CardContent className="space-y-5 p-4 sm:p-6">
        <input
          ref={fileRef}
          type="file"
          accept={ALLOWED_TYPES.join(",")}
          multiple
          className="sr-only"
          tabIndex={-1}
          aria-hidden
          disabled={isUploading}
          onChange={(e) => {
            if (e.target.files?.length) void handleFiles(e.target.files);
          }}
        />

        {images.length === 0 ? (
          <div className="grid place-items-center rounded-2xl border border-dashed py-12 text-center">
            <Image2 set="bulk" size={40} primaryColor="#BDBDBD" />
            <p className="mt-3 text-sm text-muted-foreground">
              هنوز تصویری ندارید — از دکمه + زیر اضافه کنید
            </p>
            <p className="mt-1 text-xs text-muted-foreground/80">
              اولین تصویر به‌عنوان کاور در نظر گرفته می‌شود
            </p>
          </div>
        ) : (
          <div className="relative overflow-hidden rounded-2xl border bg-[#FAFAFA] shadow-soft">
            <div className="relative aspect-[4/3] sm:aspect-[16/10]">
              {activeImage && (
                <Image
                  src={activeImage.url}
                  alt=""
                  fill
                  unoptimized={activeImage.url.startsWith("blob:")}
                  className="object-contain p-4"
                  sizes="(max-width:768px) 100vw, 720px"
                />
              )}
            </div>

            {activeImage?.is_primary && (
              <span className="absolute start-4 top-4 rounded-full bg-primary px-3 py-1 text-xs font-bold text-white shadow">
                کاور اصلی
              </span>
            )}

            <span className="absolute end-4 top-4 rounded-full bg-black/50 px-3 py-1 text-xs font-bold text-white tnum">
              {toPersianDigits(activeIndex + 1)} / {formatNumber(images.length)}
            </span>

            <div className="absolute inset-x-0 bottom-0 flex items-center justify-between gap-2 bg-gradient-to-t from-black/50 to-transparent p-4">
              <Button
                type="button"
                size="sm"
                variant="ghost"
                className="bg-white/95 text-foreground"
                disabled={activeIndex === 0}
                onClick={(e) => {
                  e.stopPropagation();
                  setActiveIndex((i) => Math.max(0, i - 1));
                }}
              >
                قبلی
              </Button>
              <div className="flex gap-1.5">
                {images.map((_, index) => (
                  <button
                    key={index}
                    type="button"
                    aria-label={`اسلاید ${index + 1}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      setActiveIndex(index);
                    }}
                    className={cn(
                      "h-2 w-2 rounded-full transition-all",
                      index === activeIndex ? "w-5 bg-white" : "bg-white/50",
                    )}
                  />
                ))}
              </div>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                className="bg-white/95 text-foreground"
                disabled={activeIndex >= images.length - 1}
                onClick={(e) => {
                  e.stopPropagation();
                  setActiveIndex((i) => Math.min(images.length - 1, i + 1));
                }}
              >
                بعدی
              </Button>
            </div>
          </div>
        )}

        {/* Thumbnails + compact add control */}
        <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
          {images.map((image, index) => (
            <button
              key={image.id}
              type="button"
              onClick={() => setActiveIndex(index)}
              className={cn(
                "relative h-20 w-20 shrink-0 overflow-hidden rounded-xl border-2 transition-all sm:h-24 sm:w-24",
                index === activeIndex
                  ? "border-primary ring-2 ring-primary/20"
                  : "border-transparent opacity-80",
              )}
            >
              <Image
                src={image.url}
                alt=""
                fill
                unoptimized={image.url.startsWith("blob:")}
                className="object-contain p-1"
                sizes="96px"
              />
              {image.is_primary && (
                <span className="absolute inset-x-0 bottom-0 bg-primary/90 py-0.5 text-[9px] font-bold text-white">
                  کاور
                </span>
              )}
            </button>
          ))}

          <button
            type="button"
            onClick={openFilePicker}
            disabled={isUploading}
            aria-label="افزودن تصویر"
            className={cn(
              "flex h-20 w-20 shrink-0 flex-col items-center justify-center gap-1 rounded-xl border-2 border-dashed border-border bg-muted/30 text-muted-foreground transition-colors sm:h-24 sm:w-24",
              "hover:border-primary/40 hover:bg-accent/40 hover:text-primary",
              isUploading && "pointer-events-none opacity-70",
            )}
          >
            {isUploading && uploadProgress ? (
              <span className="text-[10px] font-bold tnum">
                {toPersianDigits(uploadProgress.current)}/
                {toPersianDigits(uploadProgress.total)}
              </span>
            ) : (
              <>
                <Plus set="bold" size={22} primaryColor="#D02327" />
                <span className="text-[10px] font-bold">افزودن</span>
              </>
            )}
          </button>
        </div>

        {activeImage && (
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              size="sm"
              disabled={setPrimary.isPending || activeImage.is_primary}
              onClick={() =>
                setPrimary.mutate(activeImage.id, {
                  onSuccess: () => toast.success("کاور اصلی تنظیم شد"),
                  onError: (err) =>
                    toast.error(err instanceof ApiError ? err.message : "خطا"),
                })
              }
            >
              انتخاب به‌عنوان کاور
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={activeIndex === 0 || reorder.isPending}
              onClick={() => moveImage(activeIndex, -1)}
            >
              <ArrowUp set="light" size={16} />
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={activeIndex >= images.length - 1 || reorder.isPending}
              onClick={() => moveImage(activeIndex, 1)}
            >
              <ArrowDown set="light" size={16} />
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              className="text-destructive"
              disabled={remove.isPending}
              onClick={() =>
                remove.mutate(activeImage.id, {
                  onSuccess: () => {
                    toast.success("تصویر حذف شد");
                    setActiveIndex(0);
                  },
                  onError: (err) =>
                    toast.error(
                      err instanceof ApiError ? err.message : "حذف ناموفق بود",
                    ),
                })
              }
            >
              <Delete set="light" size={16} />
              حذف
            </Button>
          </div>
        )}

        <div className="rounded-xl border bg-muted/20 p-4">
          <Field label="افزودن تصویر از لینک URL" htmlFor="image_url">
            <div className="flex flex-col gap-2 sm:flex-row">
              <Input
                id="image_url"
                value={imageUrl}
                onChange={(e) => setImageUrl(e.target.value)}
                placeholder="https://example.com/image.jpg"
                dir="ltr"
                className="text-start"
              />
              <Button
                type="button"
                className="shrink-0 gap-2"
                onClick={() => void handleAddUrl()}
                disabled={addUrl.isPending || !imageUrl.trim()}
              >
                <Paper set="light" size={18} />
                افزودن لینک
              </Button>
            </div>
          </Field>
        </div>
      </CardContent>
    </Card>
  );
}
