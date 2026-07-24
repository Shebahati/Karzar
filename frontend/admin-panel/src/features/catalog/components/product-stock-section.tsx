"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useAdjustProductStock, useProductStock } from "@/features/catalog/queries";
import { ApiError } from "@/lib/api-client";
import { STOCK_UNIT_LABELS } from "@/types/product";

export function ProductStockSection({ productId }: { productId: number }) {
  const { data: stock, isPending } = useProductStock(productId);
  const adjust = useAdjustProductStock(productId);
  const [delta, setDelta] = useState("");
  const [reason, setReason] = useState("");

  async function handleAdjust(sign: 1 | -1) {
    const amount = Number(delta);
    if (!amount || Number.isNaN(amount) || amount <= 0) {
      toast.error("مقدار تعدیل را وارد کنید");
      return;
    }
    try {
      await adjust.mutateAsync({ delta: sign * amount, reason: reason.trim() || null });
      toast.success("موجودی به‌روزرسانی شد");
      setDelta("");
      setReason("");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "تعدیل موجودی ناموفق بود");
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>موجودی / انبار</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        {isPending ? (
          <Skeleton className="h-16 w-full" />
        ) : stock ? (
          <>
            <div className="rounded-xl bg-[#F7F7F7] p-4">
              <p className="text-sm text-muted-foreground">موجودی فعلی</p>
              <p className="mt-1 text-2xl font-bold tnum">
                {Number(stock.quantity ?? stock.stock_quantity).toLocaleString("fa-IR")}{" "}
                {stock.unit ? STOCK_UNIT_LABELS[stock.unit] : ""}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                {stock.availability ? "قابل فروش" : "ناموجود"}
                {stock.low_stock ? " · موجودی کم" : ""}
              </p>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="مقدار تعدیل" htmlFor="stock-delta">
                <Input
                  id="stock-delta"
                  dir="ltr"
                  inputMode="decimal"
                  className="tnum"
                  value={delta}
                  onChange={(e) => setDelta(e.target.value)}
                />
              </Field>
              <Field label="دلیل (اختیاری)" htmlFor="stock-reason">
                <Input
                  id="stock-reason"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
              </Field>
            </div>

            <div className="flex gap-2">
              <Button type="button" onClick={() => void handleAdjust(1)} disabled={adjust.isPending}>
                افزایش موجودی
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => void handleAdjust(-1)}
                disabled={adjust.isPending}
              >
                کاهش موجودی
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
