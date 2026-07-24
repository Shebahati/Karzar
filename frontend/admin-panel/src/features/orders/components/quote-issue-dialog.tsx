"use client";

import { useMemo, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { DateTimePicker } from "@/components/ui/datetime-picker";
import { useIssueQuote } from "@/features/orders/queries";
import { ApiError } from "@/lib/api-client";
import { formatNumber, formatToman, toEnglishDigits, toPersianDigits } from "@/lib/utils";
import type { OrderDetail } from "@/types/order";

interface QuoteIssueDialogProps {
  order: OrderDetail;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function QuoteIssueDialog({ order, open, onOpenChange }: QuoteIssueDialogProps) {
  const issueQuote = useIssueQuote(order.id);

  const [prices, setPrices] = useState<Record<number, string>>(() =>
    Object.fromEntries(
      order.items.map((item) => [
        item.product_id,
        item.unit_price ?? "",
      ]),
    ),
  );
  const [note, setNote] = useState(order.note ?? "");
  const [validUntil, setValidUntil] = useState("");

  const total = useMemo(() => {
    return order.items.reduce((sum, item) => {
      const unit = Number(toEnglishDigits(prices[item.product_id] ?? "0"));
      if (Number.isNaN(unit)) return sum;
      return sum + unit * item.quantity;
    }, 0);
  }, [order.items, prices]);

  const allPriced = order.items.every((item) => {
    const v = Number(toEnglishDigits(prices[item.product_id] ?? ""));
    return !Number.isNaN(v) && v > 0;
  });

  async function handleSubmit() {
    if (!allPriced) {
      toast.error("قیمت همه اقلام باید مشخص شود.");
      return;
    }

    try {
      await issueQuote.mutateAsync({
        items: order.items.map((item) => ({
          product_id: item.product_id,
          quantity: item.quantity,
          unit_price: toEnglishDigits(prices[item.product_id] ?? "0"),
        })),
        note: note.trim() || null,
        valid_until: validUntil || null,
      });
      toast.success("پیش‌فاکتور صادر شد.");
      onOpenChange(false);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "صدور پیش‌فاکتور ناموفق بود.");
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>صدور پیش‌فاکتور</DialogTitle>
          <DialogDescription>
            قیمت واحد هر قلم را تعیین کنید. پس از تأیید، پیش‌فاکتور برای مشتری قابل مشاهده خواهد بود.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="rounded-xl bg-muted/60 p-4 text-sm">
            <p className="font-bold">{order.customer_name}</p>
            <p className="tnum text-muted-foreground">{toPersianDigits(order.customer_phone)}</p>
          </div>

          <ul className="divide-y divide-border rounded-xl border border-border">
            {order.items.map((item) => (
              <li key={item.product_id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <p className="text-sm font-bold">{item.product_name}</p>
                  <p className="text-xs text-muted-foreground tnum">
                    {item.sku} — تعداد: {formatNumber(item.quantity)}
                  </p>
                </div>
                <Field label="قیمت واحد (تومان)" htmlFor={`price-${item.product_id}`} className="w-full sm:w-44">
                  <Input
                    id={`price-${item.product_id}`}
                    inputMode="numeric"
                    value={toPersianDigits(prices[item.product_id] ?? "")}
                    onChange={(e) =>
                      setPrices((prev) => ({
                        ...prev,
                        [item.product_id]: toEnglishDigits(e.target.value).replace(/[^\d]/g, ""),
                      }))
                    }
                    className="tnum"
                    placeholder="۰"
                  />
                </Field>
              </li>
            ))}
          </ul>

          <div className="flex items-center justify-between rounded-xl bg-accent px-4 py-3">
            <span className="text-sm font-bold">جمع پیش‌فاکتور</span>
            <span className="text-lg font-bold text-primary tnum">{formatToman(total)}</span>
          </div>

          <Field label="اعتبار پیش‌فاکتور تا" htmlFor="quote-valid">
            <DateTimePicker value={validUntil} onChange={setValidUntil} />
          </Field>

          <Field label="توضیحات برای مشتری" htmlFor="quote-note">
            <Textarea
              id="quote-note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={3}
              placeholder="شرایط پرداخت، زمان تحویل، یا توضیحات فنی"
            />
          </Field>
        </div>

        <DialogFooter className="flex-col gap-2 sm:flex-row">
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            انصراف
          </Button>
          <Button
            type="button"
            disabled={!allPriced || issueQuote.isPending}
            onClick={() => void handleSubmit()}
          >
            {issueQuote.isPending ? "در حال صدور…" : "صدور پیش‌فاکتور"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
