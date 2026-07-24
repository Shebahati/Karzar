"use client";

import { useMemo, useState } from "react";
import { Danger, Lock } from "react-iconly";
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
import { CategoryLeafCombobox } from "@/features/catalog/components/category-leaf-combobox";
import { useDeleteCategory, useFlatCategories, useVerifyPin } from "@/features/catalog/queries";
import { enrichFlatCategories } from "@/features/catalog/utils/category-tree";
import { stepUpPinSchema } from "@/lib/validation";
import { ApiError } from "@/lib/api-client";
import type { CategoryFlat } from "@/types/category";

interface CategoryDeleteDialogProps {
  category: CategoryFlat | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDeleted?: () => void;
}

export function CategoryDeleteDialog({
  category,
  open,
  onOpenChange,
  onDeleted,
}: CategoryDeleteDialogProps) {
  const [pin, setPin] = useState("");
  const [targetId, setTargetId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const verifyPin = useVerifyPin();
  const deleteCategory = useDeleteCategory();
  const { data: raw = [] } = useFlatCategories();
  const categories = useMemo(() => enrichFlatCategories(raw), [raw]);

  const pending = verifyPin.isPending || deleteCategory.isPending;
  const productCount = category?.product_count ?? 0;
  const needsTarget = productCount > 0;

  const selectableLeaves = useMemo(
    () => categories.filter((c) => c.is_selectable && c.id !== category?.id),
    [categories, category?.id],
  );

  function handleClose(next: boolean) {
    if (!pending) {
      onOpenChange(next);
      if (!next) {
        setPin("");
        setTargetId("");
        setError(null);
      }
    }
  }

  async function handleConfirm() {
    if (!category) return;
    setError(null);

    const targetNum = targetId ? Number(targetId) : NaN;
    if (needsTarget && !Number.isFinite(targetNum)) {
      setError("برای انتقال محصولات، یک دستهٔ برگ عمق ۳ انتخاب کنید.");
      return;
    }

    const parsed = stepUpPinSchema.safeParse(pin);
    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message ?? "کد امنیتی نامعتبر است.");
      return;
    }

    try {
      const { secure_token } = await verifyPin.mutateAsync(parsed.data);
      const result = await deleteCategory.mutateAsync({
        id: category.id,
        stepUpToken: secure_token,
        targetCategoryId: needsTarget ? targetNum : undefined,
      });
      toast.success("دسته‌بندی حذف شد", {
        description: `${result.products_reassigned.toLocaleString("fa-IR")} محصول منتقل شد.`,
      });
      onOpenChange(false);
      setPin("");
      setTargetId("");
      onDeleted?.();
    } catch (err) {
      const message =
        err instanceof ApiError
          ? (err.fieldErrors.target_category_id ??
            err.fieldErrors.pin ??
            err.message)
          : "حذف دسته‌بندی ناموفق بود.";
      setError(message);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-lg border-transparent shadow-[0_8px_40px_rgba(0,0,0,0.12)]">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-destructive/10 text-destructive">
          <Danger set="bulk" size={28} primaryColor="#C22026" />
        </div>
        <DialogHeader>
          <DialogTitle className="text-[#4F4F4F]">حذف دسته‌بندی</DialogTitle>
          <DialogDescription>
            {category
              ? `«${category.name}» — لایه ${category.depth} · ${productCount.toLocaleString("fa-IR")} محصول`
              : ""}
          </DialogDescription>
        </DialogHeader>

        {category && (
          <p className="rounded-xl bg-[#FFF5F5] p-4 text-sm leading-relaxed text-[#4F4F4F]">
            {needsTarget
              ? "این دسته محصول دارد. محصولات فقط به یک دستهٔ برگ قابل‌انتخاب (عمق ۳) منتقل می‌شوند — انتقال به والد مجاز نیست."
              : "این دسته خالی است و بدون انتقال محصول حذف می‌شود."}
          </p>
        )}

        {needsTarget && (
          <Field label="دستهٔ مقصد (برگ عمق ۳)" htmlFor="category-delete-target">
            <CategoryLeafCombobox
              categories={selectableLeaves}
              value={targetId}
              onChange={setTargetId}
              disabled={pending}
            />
          </Field>
        )}

        <Field
          label="کد امنیتی ۶ رقمی (PIN)"
          htmlFor="category-delete-pin"
          error={error ?? undefined}
        >
          <div className="relative">
            <span className="pointer-events-none absolute inset-y-0 start-3 flex items-center text-muted-foreground">
              <Lock set="light" size={18} />
            </span>
            <Input
              id="category-delete-pin"
              type="password"
              inputMode="numeric"
              maxLength={12}
              dir="ltr"
              className="ps-10 text-center tracking-[0.4em]"
              value={pin}
              onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))}
              onKeyDown={(e) => {
                if (e.key === "Enter") void handleConfirm();
              }}
              disabled={pending}
            />
          </div>
        </Field>

        <div className="flex gap-3">
          <Button
            type="button"
            variant="destructive"
            className="flex-1"
            disabled={pending}
            onClick={() => void handleConfirm()}
          >
            {pending ? "در حال حذف..." : "تأیید و حذف"}
          </Button>
          <Button type="button" variant="ghost" disabled={pending} onClick={() => handleClose(false)}>
            انصراف
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
