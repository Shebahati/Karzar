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
import { useUpdateOrderStatus } from "@/features/orders/queries";
import { ApiError } from "@/lib/api-client";
import { formatToman, toPersianDigits } from "@/lib/utils";
import type { OrderDetail } from "@/types/order";

interface ShipOrderDialogProps {
  order: OrderDetail;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ShipOrderDialog({ order, open, onOpenChange }: ShipOrderDialogProps) {
  const updateStatus = useUpdateOrderStatus(order.id);
  const [postalCode, setPostalCode] = useState(order.postal_tracking_code ?? "");
  const [deliveryEta, setDeliveryEta] = useState(order.delivery_eta ?? "");
  const [note, setNote] = useState("");

  const canSubmit = postalCode.trim().length >= 10;

  async function handleSubmit() {
    if (!canSubmit) {
      toast.error("کد رهگیری پست باید حداقل ۱۰ رقم باشد.");
      return;
    }

    try {
      await updateStatus.mutateAsync({
        status: "shipped",
        postal_tracking_code: postalCode.trim(),
        delivery_eta: deliveryEta || null,
        note: note.trim() || null,
      });
      toast.success("اطلاعات ارسال ثبت شد.");
      onOpenChange(false);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "ثبت ارسال ناموفق بود.");
    }
  }

  const itemCount = useMemo(
    () => order.items.reduce((sum, item) => sum + item.quantity, 0),
    [order.items],
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>ثبت ارسال سفارش</DialogTitle>
          <DialogDescription>
            کد رهگیری پست را وارد کنید تا در پیگیری مشتری و پیامک نمایش داده شود.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="rounded-xl bg-muted/60 p-4 text-sm">
            <p className="font-bold text-foreground tnum">{toPersianDigits(order.tracking_code)}</p>
            <p className="mt-1 text-muted-foreground">
              {order.customer_name} — {toPersianDigits(itemCount)} قلم
            </p>
            <p className="mt-1 font-bold tnum">{formatToman(order.estimated_total)}</p>
          </div>

          <Field label="کد رهگیری اداره پست *" htmlFor="ship-postal">
            <Input
              id="ship-postal"
              value={postalCode}
              onChange={(e) => setPostalCode(e.target.value)}
              placeholder="مثال: ۱۲۳۴۵۶۷۸۹۰۱۲۳۴۵۶"
              className="tnum"
            />
          </Field>

          <Field label="زمان تحویل تقریبی" htmlFor="ship-eta">
            <DateTimePicker value={deliveryEta} onChange={setDeliveryEta} />
          </Field>

          <Field label="یادداشت داخلی (اختیاری)" htmlFor="ship-note">
            <Textarea
              id="ship-note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={2}
              placeholder="مثلاً: ارسال با تیپاکس"
            />
          </Field>
        </div>

        <DialogFooter className="flex-col gap-2 sm:flex-row">
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            انصراف
          </Button>
          <Button type="button" disabled={!canSubmit || updateStatus.isPending} onClick={() => void handleSubmit()}>
            {updateStatus.isPending ? "در حال ثبت…" : "تأیید و ارسال"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
