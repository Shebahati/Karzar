"use client";

import { useMemo } from "react";
import Link from "next/link";
import { Bag2, Delete } from "react-iconly";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StepUpDialog } from "@/components/step-up-dialog";
import { useProducts, useRestoreProduct } from "@/features/catalog/queries";
import { ApiError } from "@/lib/api-client";
import { env } from "@/config/env";
import { useState } from "react";

export default function DeletedProductsPage() {
  const listParams = useMemo(() => ({ limit: 50, is_deleted: true }), []);
  const { data, isPending, isError, error, refetch } = useProducts(listParams);
  const restoreProduct = useRestoreProduct();
  const products = data?.data ?? [];
  const [restoreId, setRestoreId] = useState<number | null>(null);

  const backendUnavailable =
    !env.USE_MOCK &&
    isError &&
    error instanceof ApiError &&
    (error.status === 400 || error.status === 422 || error.code === "VALIDATION_FAILED");

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-[#4F4F4F]">محصولات حذف‌شده</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            بازیابی محصولات soft-delete شده
          </p>
        </div>
        <Button asChild variant="outline">
          <Link href="/catalog/products">بازگشت به محصولات</Link>
        </Button>
      </div>

      {backendUnavailable ? (
        <Card>
          <CardContent className="py-16 text-center text-sm leading-7 text-muted-foreground">
            <p className="font-bold text-foreground">این قابلیت هنوز در API فعال نیست</p>
            <p className="mt-2">
              فیلتر <code dir="ltr">is_deleted</code> باید توسط تیم بک‌اند پیاده‌سازی شود.
              جزئیات در <code dir="ltr">BACKEND_HANDOFF.md</code> آمده است.
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            {isPending ? (
              <div className="space-y-3 p-6">
                <Skeleton className="h-14 w-full" />
                <Skeleton className="h-14 w-full" />
              </div>
            ) : isError ? (
              <div className="py-16 text-center text-sm">
                {error instanceof ApiError ? error.message : "خطا در دریافت لیست"}
                <div className="mt-3">
                  <Button size="sm" variant="outline" onClick={() => refetch()}>
                    تلاش مجدد
                  </Button>
                </div>
              </div>
            ) : products.length === 0 ? (
              <div className="flex flex-col items-center gap-3 py-16 text-center">
                <Delete set="bulk" size={44} primaryColor="#BDBDBD" />
                <p className="text-sm font-bold">محصول حذف‌شده‌ای وجود ندارد</p>
              </div>
            ) : (
              <ul className="divide-y divide-gray-100">
                {products.map((product) => (
                  <li
                    key={product.id}
                    className="flex flex-wrap items-center justify-between gap-4 px-4 py-4 hover:bg-[#F7F7F7]"
                  >
                    <div className="flex items-center gap-3">
                      <span className="grid h-10 w-10 place-items-center rounded-lg bg-accent text-primary">
                        <Bag2 set="bulk" size={20} primaryColor="#C22026" />
                      </span>
                      <div>
                        <p className="text-sm font-bold">{product.name}</p>
                        <p className="text-xs text-muted-foreground tnum">{product.sku}</p>
                      </div>
                    </div>
                    <Button
                      size="sm"
                      disabled={restoreProduct.isPending}
                      onClick={() => setRestoreId(product.id)}
                    >
                      بازیابی
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )}

      <StepUpDialog
        open={restoreId != null}
        onOpenChange={(open) => {
          if (!open) setRestoreId(null);
        }}
        title="تأیید بازیابی"
        description="بازیابی محصول نیاز به کد PIN امنیتی دارد."
        onVerified={(token) => {
          if (restoreId == null) return;
          restoreProduct.mutate(
            { id: restoreId, stepUpToken: token },
            {
              onSuccess: () => {
                toast.success("محصول بازیابی شد");
                setRestoreId(null);
              },
              onError: (err) =>
                toast.error(err instanceof ApiError ? err.message : "بازیابی ناموفق بود"),
            },
          );
        }}
      />
    </div>
  );
}
