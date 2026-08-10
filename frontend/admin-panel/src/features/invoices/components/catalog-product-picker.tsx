"use client";

import { useState } from "react";

import { useProducts } from "@/features/catalog/queries";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { cn, formatToman } from "@/lib/utils";
import type { ProductSummary } from "@/types/product";

export function CatalogProductPicker({
  open,
  onOpenChange,
  onPick,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onPick: (product: ProductSummary) => void;
}) {
  const [q, setQ] = useState("");
  const { data, isPending } = useProducts({
    limit: 40,
    search: q.trim() || undefined,
  });
  const rows = data?.data ?? [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] max-w-lg overflow-hidden">
        <DialogHeader>
          <DialogTitle>انتخاب از کاتالوگ</DialogTitle>
          <DialogDescription>
            قیمت واحد از کاتالوگ پر می‌شود و بعداً قابل ویرایش است.
          </DialogDescription>
        </DialogHeader>

        <Input
          placeholder="جستجوی نام یا SKU…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />

        <div className="max-h-[42vh] space-y-1 overflow-y-auto rounded-xl bg-muted/40 p-2">
          {isPending ? (
            <p className="p-3 text-sm text-muted-foreground">در حال بارگذاری…</p>
          ) : rows.length === 0 ? (
            <p className="p-3 text-sm text-muted-foreground">محصولی یافت نشد</p>
          ) : (
            rows.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => {
                  onPick(p);
                  onOpenChange(false);
                  setQ("");
                }}
                className={cn(
                  "flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-start text-sm transition hover:bg-card",
                )}
              >
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-bold text-ink">{p.name}</span>
                  <span className="mt-0.5 block text-[11px] text-muted-foreground" dir="ltr">
                    {p.sku}
                  </span>
                </span>
                <span className="shrink-0 text-xs font-bold text-[#4F4F4F] tnum">
                  {formatToman(p.base_price)}
                </span>
              </button>
            ))
          )}
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            بستن
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
