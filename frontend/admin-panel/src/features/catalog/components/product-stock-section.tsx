"use client";

import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useProductStock, useSetProductAvailability } from "@/features/catalog/queries";
import { ApiError } from "@/lib/api-client";

export function ProductStockSection({ productId }: { productId: number }) {
  const { data: stock, isPending } = useProductStock(productId);
  const setAvailability = useSetProductAvailability(productId);

  async function handleToggle(next: boolean) {
    try {
      await setAvailability.mutateAsync({
        is_available: next,
        reason: next ? "mark_available" : "mark_unavailable",
      });
      toast.success(next ? "محصول موجود شد" : "محصول ناموجود شد");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "به‌روزرسانی موجودی ناموفق بود");
    }
  }

  const available = Boolean(stock?.is_available ?? stock?.availability);

  return (
    <Card>
      <CardHeader>
        <CardTitle>وضعیت موجودی (سایت)</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        {isPending ? (
          <Skeleton className="h-16 w-full" />
        ) : stock ? (
          <>
            <div className="rounded-xl bg-[#F7F7F7] p-4">
              <p className="text-sm text-muted-foreground">نمایش در فروشگاه</p>
              <p className="mt-1 text-2xl font-bold">{available ? "موجود" : "ناموجود"}</p>
              <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
                تعداد انبار فقط در حسابفا نگهداری می‌شود. سایت فقط موجود / ناموجود نشان می‌دهد.
              </p>
            </div>

            <div className="flex gap-2">
              <Button
                type="button"
                onClick={() => void handleToggle(true)}
                disabled={setAvailability.isPending || available}
              >
                موجود
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => void handleToggle(false)}
                disabled={setAvailability.isPending || !available}
              >
                ناموجود
              </Button>
            </div>
          </>
        ) : (
          <p className="text-sm text-muted-foreground">اطلاعات موجودی در دسترس نیست.</p>
        )}
      </CardContent>
    </Card>
  );
}
