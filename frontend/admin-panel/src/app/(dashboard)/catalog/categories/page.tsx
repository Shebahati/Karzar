"use client";

import { useMemo, useState } from "react";
import { Category, Star } from "react-iconly";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { BrandsManagementModal } from "@/features/catalog/components/brands-management-modal";
import { CategoryColumns } from "@/features/catalog/components/category-columns";
import { CategoryDeleteDialog } from "@/features/catalog/components/category-delete-dialog";
import {
  CategoryFormDialog,
  toCreatePayload,
  toUpdatePayload,
  type CategoryFormValues,
} from "@/features/catalog/components/category-form-dialog";
import {
  useCreateCategory,
  useFlatCategories,
  useUpdateCategory,
} from "@/features/catalog/queries";
import { enrichFlatCategories } from "@/features/catalog/utils/category-tree";
import { ApiError } from "@/lib/api-client";
import type { CategoryFlat } from "@/types/category";

type FormMode = {
  open: boolean;
  mode: "create" | "edit";
  layer: 1 | 2 | 3;
  parentId?: number | null;
  category?: CategoryFlat | null;
};

export default function CategoriesPage() {
  const { data: rawCategories = [], isPending } = useFlatCategories();
  const categories = useMemo(() => enrichFlatCategories(rawCategories), [rawCategories]);

  const createCategory = useCreateCategory();
  const updateCategory = useUpdateCategory();

  const [layer1Id, setLayer1Id] = useState<number | null>(null);
  const [layer2Id, setLayer2Id] = useState<number | null>(null);
  const [brandsOpen, setBrandsOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<CategoryFlat | null>(null);
  const [form, setForm] = useState<FormMode>({
    open: false,
    mode: "create",
    layer: 1,
  });

  function openCreate(layer: 1 | 2 | 3) {
    const parentId =
      layer === 2 ? layer1Id : layer === 3 ? layer2Id : null;
    setForm({ open: true, mode: "create", layer, parentId });
  }

  function openEdit(category: CategoryFlat) {
    setForm({
      open: true,
      mode: "edit",
      layer: category.depth as 1 | 2 | 3,
      category,
    });
  }

  async function handleFormSubmit(values: CategoryFormValues) {
    try {
      if (form.mode === "create") {
        await createCategory.mutateAsync(
          toCreatePayload(values, form.layer === 1 ? null : form.parentId ?? null),
        );
        toast.success("دسته‌بندی ایجاد شد");
      } else if (form.category) {
        await updateCategory.mutateAsync({
          id: form.category.id,
          payload: toUpdatePayload(values),
        });
        toast.success("دسته‌بندی به‌روزرسانی شد");
      }
      setForm((prev) => ({ ...prev, open: false }));
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "ذخیره ناموفق بود");
      throw err;
    }
  }

  function handleDeleted() {
    if (deleteTarget?.id === layer2Id) setLayer2Id(null);
    if (deleteTarget?.id === layer1Id) {
      setLayer1Id(null);
      setLayer2Id(null);
    }
    setDeleteTarget(null);
  }

  const layerLabels = { 1: "دسته اصلی", 2: "زیردسته", 3: "دسته محصول" } as const;

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-accent text-primary">
            <Category set="bulk" size={26} primaryColor="#C22026" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-[#4F4F4F]">دسته‌بندی‌ها</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              مدیریت سه‌لایه درخت دسته‌بندی محصولات
            </p>
          </div>
        </div>
        <Button onClick={() => setBrandsOpen(true)}>
          <Star set="bold" size={18} primaryColor="#FFFFFF" />
          مدیریت برندها
        </Button>
      </div>

      {isPending ? (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Skeleton className="h-[420px] w-full rounded-xl" />
          <Skeleton className="h-[420px] w-full rounded-xl" />
          <Skeleton className="h-[420px] w-full rounded-xl" />
        </div>
      ) : (
        <CategoryColumns
          categories={categories}
          layer1Id={layer1Id}
          layer2Id={layer2Id}
          onSelectLayer1={(id) => {
            setLayer1Id(id);
            setLayer2Id(null);
          }}
          onSelectLayer2={setLayer2Id}
          onAddLayer1={() => openCreate(1)}
          onAddLayer2={() => openCreate(2)}
          onAddLayer3={() => openCreate(3)}
          onEdit={openEdit}
          onDelete={setDeleteTarget}
        />
      )}

      <BrandsManagementModal open={brandsOpen} onOpenChange={setBrandsOpen} />

      <CategoryFormDialog
        open={form.open}
        onOpenChange={(open) => setForm((prev) => ({ ...prev, open }))}
        mode={form.mode}
        layerLabel={layerLabels[form.layer]}
        parentId={form.parentId}
        category={form.category}
        onSubmit={handleFormSubmit}
        pending={createCategory.isPending || updateCategory.isPending}
      />

      <CategoryDeleteDialog
        category={deleteTarget}
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
        onDeleted={handleDeleted}
      />
    </div>
  );
}
