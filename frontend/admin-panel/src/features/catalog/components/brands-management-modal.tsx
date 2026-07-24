"use client";

import { useState } from "react";
import { Delete, Edit, Plus, Star } from "react-iconly";
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

  const [editing, setEditing] = useState<Brand | null>(null);
  const [name, setName] = useState("");
  const [country, setCountry] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<Brand | null>(null);

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
    const brandName = deleteTarget.name;
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

  const pending = createBrand.isPending || updateBrand.isPending;

  return (
    <>
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
            <Star set="bulk" size={28} primaryColor="#C22026" />
          </div>
          <DialogHeader>
            <DialogTitle className="text-[#4F4F4F]">مدیریت برندها</DialogTitle>
            <DialogDescription>افزودن، ویرایش و حذف برندهای فروشگاه</DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-4 rounded-xl bg-[#F7F7F7] p-4 shadow-sm md:grid-cols-[1fr_1fr_auto]">
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
                    <div className="min-w-0">
                      <p className="truncate text-sm font-bold text-[#4F4F4F]">{brand.name}</p>
                      {brand.country && (
                        <p className="text-xs text-muted-foreground">{brand.country}</p>
                      )}
                    </div>
                    <div className="flex shrink-0 gap-1">
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
