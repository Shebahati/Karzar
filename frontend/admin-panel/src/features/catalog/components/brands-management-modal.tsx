"use client";

import { useRef, useState } from "react";
import Image from "next/image";
import { Delete, Edit, Plus, Star, Upload } from "react-iconly";
import { toast } from "sonner";

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
import { Skeleton } from "@/components/ui/skeleton";
import { StepUpDialog } from "@/components/step-up-dialog";
import {
  useBrands,
  useCreateBrand,
  useDeleteBrand,
  useUpdateBrand,
  useUploadBrandLogo,
} from "@/features/catalog/queries";
import { ApiError } from "@/lib/api-client";
import type { Brand } from "@/types/category";

interface BrandsManagementModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function BrandsManagementModal({ open, onOpenChange }: BrandsManagementModalProps) {
  const { data: brands = [], isPending } = useBrands();
  const createBrand = useCreateBrand();
  const updateBrand = useUpdateBrand();
  const deleteBrand = useDeleteBrand();
  const uploadLogo = useUploadBrandLogo();

  const [editing, setEditing] = useState<Brand | null>(null);
  const [name, setName] = useState("");
  const [country, setCountry] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<Brand | null>(null);
  const [logoTargetId, setLogoTargetId] = useState<number | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  function resetForm() {
    setEditing(null);
    setName("");
    setCountry("");
  }

  function startEdit(brand: Brand) {
    setEditing(brand);
    setName(brand.name);
    setCountry(brand.country ?? "");
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) {
      toast.error("نام برند الزامی است.");
      return;
    }

    try {
      if (editing) {
        await updateBrand.mutateAsync({
          id: editing.id,
          payload: { name: trimmed, country: country.trim() || null },
        });
        toast.success("برند به‌روزرسانی شد");
      } else {
        await createBrand.mutateAsync({
          name: trimmed,
          country: country.trim() || null,
        });
        toast.success("برند جدید ثبت شد");
      }
      resetForm();
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "عملیات ناموفق بود");
    }
  }

  function handleDeleteVerified(stepUpToken: string) {
    if (!deleteTarget) return;
    deleteBrand.mutate(
      { id: deleteTarget.id, stepUpToken },
      {
        onSuccess: (result) => {
          toast.success("برند حذف شد", {
            description: `${result.products_cleared} محصول از این برند جدا شد.`,
          });
          if (editing?.id === deleteTarget.id) resetForm();
          setDeleteTarget(null);
        },
        onError: (err) => {
          toast.error(err instanceof ApiError ? err.message : "حذف ناموفق بود");
          setDeleteTarget(null);
        },
      },
    );
  }

  function pickLogo(brandId: number) {
    setLogoTargetId(brandId);
    fileRef.current?.click();
  }

  async function onLogoSelected(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    const brandId = logoTargetId;
    e.target.value = "";
    setLogoTargetId(null);
    if (!file || brandId == null) return;
    try {
      await uploadLogo.mutateAsync({ id: brandId, file });
      toast.success("لوگوی برند ذخیره شد");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "آپلود لوگو ناموفق بود");
    }
  }

  const pending = createBrand.isPending || updateBrand.isPending;

  return (
    <>
      <input
        ref={fileRef}
        type="file"
        accept="image/png,image/jpeg,image/webp,image/gif,image/svg+xml"
        className="hidden"
        onChange={onLogoSelected}
      />

      <Dialog
        open={open}
        onOpenChange={(next) => {
          if (!pending) {
            onOpenChange(next);
            if (!next) resetForm();
          }
        }}
      >
        <DialogContent className="max-h-[90vh] max-w-3xl overflow-y-auto border-white/40 bg-white/90 shadow-[0_8px_40px_rgba(0,0,0,0.12)] backdrop-blur-xl">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-accent text-primary">
            <Star set="bulk" size={28} primaryColor="#D02327" />
          </div>
          <DialogHeader>
            <DialogTitle className="text-[#4F4F4F]">مدیریت برندها</DialogTitle>
            <DialogDescription>
              افزودن، ویرایش، لوگو و حذف برندهای فروشگاه
            </DialogDescription>
          </DialogHeader>

          <form
            onSubmit={handleSubmit}
            className="grid grid-cols-1 gap-4 rounded-xl bg-[#F7F7F7] p-4 shadow-sm md:grid-cols-[1fr_1fr_auto]"
          >
            <Field label="نام برند" htmlFor="brand-name" required>
              <Input
                id="brand-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="مثال: Mitutoyo | میتوتویو"
              />
            </Field>
            <Field label="کشور" htmlFor="brand-country">
              <Input
                id="brand-country"
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                placeholder="اختیاری"
              />
            </Field>
            <div className="flex items-end gap-2">
              <Button type="submit" disabled={pending}>
                <Plus set="bold" size={18} primaryColor="#FFFFFF" />
                {editing ? "ذخیره" : "افزودن"}
              </Button>
              {editing && (
                <Button type="button" variant="ghost" onClick={resetForm}>
                  انصراف
                </Button>
              )}
            </div>
          </form>

          <div className="rounded-xl bg-white shadow-sm">
            {isPending ? (
              <div className="flex flex-col gap-2 p-4">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </div>
            ) : brands.length === 0 ? (
              <p className="p-8 text-center text-sm text-muted-foreground">برندی ثبت نشده است.</p>
            ) : (
              <ul className="divide-y divide-gray-100">
                {brands.map((brand) => (
                  <li
                    key={brand.id}
                    className="flex items-center justify-between gap-3 px-4 py-3 transition-colors hover:bg-[#F7F7F7]"
                  >
                    <div className="flex min-w-0 items-center gap-3">
                      <span className="grid h-11 w-11 shrink-0 place-items-center overflow-hidden rounded-xl bg-[#F7F7F7] text-sm font-bold text-muted-foreground">
                        {brand.logo_url ? (
                          // next/image remote config already allows api uploads
                          <Image
                            src={brand.logo_url}
                            alt=""
                            width={44}
                            height={44}
                            className="object-contain p-1"
                            unoptimized={brand.logo_url.endsWith(".svg")}
                          />
                        ) : (
                          (brand.name || "B").slice(0, 1)
                        )}
                      </span>
                      <div className="min-w-0">
                        <p className="truncate text-sm font-bold text-[#4F4F4F]">{brand.name}</p>
                        {brand.country && (
                          <p className="text-xs text-muted-foreground">{brand.country}</p>
                        )}
                      </div>
                    </div>
                    <div className="flex shrink-0 gap-1">
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        aria-label="آپلود لوگو"
                        disabled={uploadLogo.isPending}
                        onClick={() => pickLogo(brand.id)}
                      >
                        <Upload set="light" size={18} primaryColor="currentColor" />
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        aria-label="ویرایش"
                        onClick={() => startEdit(brand)}
                      >
                        <Edit set="light" size={18} primaryColor="currentColor" />
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        aria-label="حذف برند"
                        className="text-destructive hover:bg-destructive/10"
                        onClick={() => setDeleteTarget(brand)}
                      >
                        <Delete set="light" size={18} primaryColor="currentColor" />
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </DialogContent>
      </Dialog>

      <StepUpDialog
        open={deleteTarget !== null}
        onOpenChange={(next) => (!next ? setDeleteTarget(null) : undefined)}
        onVerified={handleDeleteVerified}
        actionPending={deleteBrand.isPending}
        title="حذف برند"
        description={
          deleteTarget
            ? `برای حذف «${deleteTarget.name}» کد امنیتی مدیر را وارد کنید.`
            : undefined
        }
      />
    </>
  );
}
