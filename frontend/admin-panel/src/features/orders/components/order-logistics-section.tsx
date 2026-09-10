"use client";

import { useState } from "react";
import { toast } from "sonner";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StepUpDialog } from "@/components/step-up-dialog";
import { shipmentActionAvailability } from "@/features/orders/shipment-actions";
import { ApiError } from "@/lib/api-client";
import { formatToman, toPersianDigits } from "@/lib/utils";
import { shippingAdminService } from "@/services/shipping";
import { ordersKeys } from "@/features/orders/queries";
import type { OrderDetail } from "@/types/order";

export function OrderLogisticsSection({ order }: { order: OrderDetail }) {
  const queryClient = useQueryClient();
  const { data: shipments = order.shipments ?? [] } = useQuery({
    queryKey: ["order-shipments", order.id],
    queryFn: () => shippingAdminService.list(order.id),
    enabled: Boolean(order.shipping_provider || (order.shipments && order.shipments.length)),
  });
  const [cancelId, setCancelId] = useState<number | null>(null);
  const [pending, setPending] = useState(false);

  if (!order.shipping_provider && shipments.length === 0) {
    return null;
  }

  async function run(label: string, fn: () => Promise<unknown>) {
    setPending(true);
    try {
      await fn();
      toast.success(label);
      void queryClient.invalidateQueries({ queryKey: ["order-shipments", order.id] });
      void queryClient.invalidateQueries({ queryKey: ordersKeys.detail(order.id) });
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "عملیات ارسال ناموفق بود.");
    } finally {
      setPending(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">ارسال و لجستیک</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid gap-2 text-sm">
          <p>
            <span className="text-muted-foreground">سرویس: </span>
            {order.shipping_carrier_code ?? "—"} {order.shipping_service_code ?? ""}
          </p>
          <p>
            <span className="text-muted-foreground">هزینه مشتری: </span>
            <span className="tnum">{formatToman(order.shipping_customer_cost)}</span>
          </p>
          <p>
            <span className="text-muted-foreground">نرخ ارائه‌دهنده: </span>
            <span className="tnum">{formatToman(order.shipping_provider_quoted_cost)}</span>
          </p>
        </div>

        {shipments.map((shipment) => {
          const actions = shipmentActionAvailability(shipment);
          return (
            <div key={shipment.internal_id} className="space-y-3 rounded-xl border border-border/60 p-4">
              <div className="flex flex-wrap gap-2 text-sm">
                <span className="font-bold">{shipment.status_label}</span>
                {shipment.provider_parcel_no && (
                  <span className="tnum">Parcel {toPersianDigits(shipment.provider_parcel_no)}</span>
                )}
                {shipment.tracking_code && (
                  <span className="tnum">رهگیری {toPersianDigits(shipment.tracking_code)}</span>
                )}
              </div>
              {shipment.package && (
                <p className="text-xs text-muted-foreground tnum">
                  بسته {toPersianDigits(shipment.package.length_cm)}×{toPersianDigits(shipment.package.width_cm)}×
                  {toPersianDigits(shipment.package.height_cm)} cm / {toPersianDigits(shipment.package.weight_grams)} g
                </p>
              )}
              {shipment.last_error_message && (
                <p className="text-xs text-destructive">{shipment.last_error_message}</p>
              )}
              {shipment.last_tracking_sync_at && (
                <p className="text-[11px] text-muted-foreground">
                  آخرین همگام‌سازی: {new Date(shipment.last_tracking_sync_at).toLocaleString("fa-IR")}
                </p>
              )}
              <ol className="space-y-2 border-s ps-3">
                {shipment.events.map((event, idx) => (
                  <li key={`${shipment.internal_id}-${idx}`}>
                    <p className="text-sm">{event.status_label}</p>
                    {event.description && <p className="text-xs text-muted-foreground">{event.description}</p>}
                  </li>
                ))}
              </ol>
              <div className="flex flex-wrap gap-2">
                {(actions.canBook || actions.canRetrySafe) && (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={pending}
                    onClick={() => void run("رزرو/تطبیق انجام شد", () => shippingAdminService.book(order.id, shipment.internal_id))}
                  >
                    ایجاد / تطبیق مرسوله
                  </Button>
                )}
                {actions.canReady && (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={pending}
                    onClick={() => void run("آماده جمع‌آوری شد", () => shippingAdminService.markReady(order.id, shipment.internal_id))}
                  >
                    آماده جمع‌آوری
                  </Button>
                )}
                {actions.canLabel && (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={pending}
                    onClick={() => void run("برچسب دریافت شد", () => shippingAdminService.downloadLabel(order.id, shipment.internal_id))}
                  >
                    دانلود برچسب
                  </Button>
                )}
                {actions.canRefresh && (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={pending}
                    onClick={() => void run("رهگیری به‌روز شد", () => shippingAdminService.refreshTracking(order.id, shipment.internal_id))}
                  >
                    تازه‌سازی رهگیری
                  </Button>
                )}
                {actions.canEdit && (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={pending}
                    onClick={() => {
                      const shipping = order.shipping ?? {};
                      void run("آدرس مرسوله به‌روز شد", () =>
                        shippingAdminService.edit(order.id, shipment.internal_id, {
                          address_line: typeof shipping.address_line === "string" ? shipping.address_line : null,
                          postal_code: typeof shipping.postal_code === "string" ? shipping.postal_code : null,
                        }),
                      );
                    }}
                  >
                    ویرایش آدرس (قبل از مهلت)
                  </Button>
                )}
                {actions.canCancel && (
                  <Button size="sm" variant="outline" className="text-destructive" onClick={() => setCancelId(shipment.internal_id)}>
                    انصراف مرسوله
                  </Button>
                )}
              </div>
            </div>
          );
        })}
      </CardContent>

      <StepUpDialog
        open={cancelId != null}
        onOpenChange={(open) => {
          if (!open) setCancelId(null);
        }}
        title="انصراف مرسوله"
        description="انصراف از ارسال نزد ارائه‌دهنده نیاز به تأیید PIN دارد. اگر مهلت گذشته باشد، انصراف جعل نمی‌شود."
        actionPending={pending}
        onVerified={async (token) => {
          if (cancelId == null) return;
          setPending(true);
          try {
            await shippingAdminService.cancel(order.id, cancelId, "admin cancel", token);
            toast.success("درخواست انصراف ثبت شد.");
            setCancelId(null);
            void queryClient.invalidateQueries({ queryKey: ["order-shipments", order.id] });
          } catch (err) {
            toast.error(err instanceof ApiError ? err.message : "انصراف ناموفق بود.");
          } finally {
            setPending(false);
          }
        }}
      />
    </Card>
  );
}
