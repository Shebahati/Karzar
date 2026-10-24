"use client";

import { useMemo, useState } from "react";
import { toast } from "sonner";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { StepUpDialog } from "@/components/step-up-dialog";
import { useBrands } from "@/features/catalog/queries";
import { brandBulkPricingService } from "@/services/brand-bulk-pricing";
import { formatNumber, formatToman } from "@/lib/utils";
import type {
  BrandBulkAdjustmentDirection,
  BrandBulkAdjustmentMode,
  BrandBulkPricingPreview,
} from "@/types/brand-bulk-pricing";

const lineStatusFa: Record<string, string> = {
  pending: "آماده اعمال",
  conflict: "تعارض",
  skipped: "رد شده",
  applied: "اعمال‌شده",
};

export default function BrandBulkPricingPage() {
  const queryClient = useQueryClient();
  const { data: brands = [] } = useBrands();
  const [brandId, setBrandId] = useState<string>("");
  const [mode, setMode] = useState<BrandBulkAdjustmentMode>("percent");
  const [direction, setDirection] = useState<BrandBulkAdjustmentDirection>("increase");
  const [amount, setAmount] = useState("10");
  const [preview, setPreview] = useState<BrandBulkPricingPreview | null>(null);
  const [confirmedOperationId, setConfirmedOperationId] = useState<number | null>(null);
  const [stepUpOpen, setStepUpOpen] = useState(false);

  const historyQuery = useQuery({
    queryKey: ["brand-bulk-pricing", "history", brandId],
    queryFn: () =>
      brandBulkPricingService.listOperations({
        brand_id: brandId ? Number(brandId) : undefined,
        limit: 20,
      }),
  });

  const previewMutation = useMutation({
    mutationFn: () =>
      brandBulkPricingService.preview({
        brand_id: Number(brandId),
        mode,
        direction,
        amount,
      }),
    onSuccess: (data) => {
      setPreview(data);
      setConfirmedOperationId(null);
      toast.success("پیش‌نمایش آماده است");
    },
    onError: () => toast.error("خطا در پیش‌نمایش"),
  });

  const confirmMutation = useMutation({
    mutationFn: () => {
      if (!preview) throw new Error("no preview");
      return brandBulkPricingService.confirm({
        brand_id: preview.brand_id,
        mode: preview.mode,
        direction: preview.direction,
        amount: preview.amount,
        manifest_sha256: preview.manifest_sha256,
      });
    },
    onSuccess: (op) => {
      setConfirmedOperationId(op.id);
      toast.success("عملیات تأیید شد");
      void queryClient.invalidateQueries({ queryKey: ["brand-bulk-pricing"] });
    },
    onError: () => toast.error("خطا در تأیید عملیات"),
  });

  const applyMutation = useMutation({
    mutationFn: (stepUpToken: string) => {
      if (!confirmedOperationId) throw new Error("no operation");
      const key = "bbp-ui-" + String(confirmedOperationId);
      return brandBulkPricingService.apply(confirmedOperationId, stepUpToken, key);
    },
    onSuccess: (result) => {
      toast.success(String(result.applied_count) + " قیمت به‌روزرسانی شد");
      setPreview(null);
      setConfirmedOperationId(null);
      void queryClient.invalidateQueries({ queryKey: ["brand-bulk-pricing"] });
    },
    onError: () => toast.error("اعمال ناموفق — پرچم سرور یا گام تأیید را بررسی کنید"),
  });

  const selectedBrandName = useMemo(
    () => brands.find((b) => String(b.id) === brandId)?.name ?? "—",
    [brands, brandId],
  );

  return (
    <div className="space-y-6 p-6" dir="rtl">
      <div>
        <h1 className="text-2xl font-bold">مدیریت گروهی قیمت‌ها</h1>
        <p className="text-muted-foreground text-sm mt-1">
          تنظیم گروهی base_price برای محصولات یک برند — فقط قیمت پایه تغییر می‌کند.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>پیش‌نمایش و تأیید</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <div>
            <label className="text-sm mb-1 block">برند</label>
            <Select value={brandId} onValueChange={setBrandId}>
              <SelectTrigger>
                <SelectValue placeholder="انتخاب برند" />
              </SelectTrigger>
              <SelectContent>
                {brands.map((brand) => (
                  <SelectItem key={brand.id} value={String(brand.id)}>
                    {brand.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="text-sm mb-1 block">نوع تغییر</label>
            <Select value={mode} onValueChange={(v) => setMode(v as BrandBulkAdjustmentMode)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="percent">درصد</SelectItem>
                <SelectItem value="fixed">مبلغ ثابت (تومان)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="text-sm mb-1 block">جهت</label>
            <Select
              value={direction}
              onValueChange={(v) => setDirection(v as BrandBulkAdjustmentDirection)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="increase">افزایش</SelectItem>
                <SelectItem value="decrease">کاهش</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="text-sm mb-1 block">مقدار</label>
            <Input value={amount} onChange={(e) => setAmount(e.target.value)} inputMode="decimal" />
          </div>
          <div className="md:col-span-2 lg:col-span-4 flex flex-wrap gap-2">
            <Button disabled={!brandId || previewMutation.isPending} onClick={() => previewMutation.mutate()}>
              پیش‌نمایش
            </Button>
            <Button
              variant="secondary"
              disabled={!preview || confirmMutation.isPending}
              onClick={() => confirmMutation.mutate()}
            >
              تأیید عملیات
            </Button>
            <Button variant="destructive" disabled={!confirmedOperationId} onClick={() => setStepUpOpen(true)}>
              اعمال (گام تأیید)
            </Button>
          </div>
        </CardContent>
      </Card>

      {preview ? (
        <Card>
          <CardHeader>
            <CardTitle>
              پیش‌نمایش — {selectedBrandName} ({formatNumber(preview.eligible_count)} قابل اعمال،{" "}
              {formatNumber(preview.conflict_count)} تعارض)
            </CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-right">
                  <th className="p-2">SKU</th>
                  <th className="p-2">قیمت فعلی</th>
                  <th className="p-2">قیمت جدید</th>
                  <th className="p-2">وضعیت</th>
                </tr>
              </thead>
              <tbody>
                {preview.lines.slice(0, 100).map((line) => (
                  <tr key={line.product_id} className="border-b border-muted/40">
                    <td className="p-2 font-mono text-xs">{line.sku}</td>
                    <td className="p-2">{line.old_base_price ? formatToman(line.old_base_price) : "—"}</td>
                    <td className="p-2">{line.new_base_price ? formatToman(line.new_base_price) : "—"}</td>
                    <td className="p-2">{lineStatusFa[line.line_status] ?? line.line_status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>تاریخچه عملیات</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {(historyQuery.data?.data ?? []).map((row) => (
            <div key={row.id} className="flex flex-wrap items-center justify-between gap-2 border-b py-2 text-sm">
              <span>
                #{row.id} — برند {row.brand_id} — {row.status}
              </span>
              <span className="text-muted-foreground text-xs">
                {new Date(row.confirmed_at).toLocaleString("fa-IR")}
              </span>
            </div>
          ))}
          {!historyQuery.data?.data?.length ? (
            <p className="text-muted-foreground text-sm">هنوز عملیاتی ثبت نشده است.</p>
          ) : null}
        </CardContent>
      </Card>

      <StepUpDialog
        open={stepUpOpen}
        onOpenChange={setStepUpOpen}
        title="اعمال گروهی قیمت"
        description="برای اعمال تغییرات قیمت پایه، PIN مدیر را وارد کنید."
        onVerified={(token) => {
          setStepUpOpen(false);
          applyMutation.mutate(token);
        }}
      />
    </div>
  );
}
