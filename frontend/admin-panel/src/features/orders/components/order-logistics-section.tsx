"use client";

import { useState } from "react";
import { toast } from "sonner";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StepUpDialog } from "@/components/step-up-dialog";
import {
  canSubmitFinalPackageHazards,
  receiverFulfillmentDisplay,
  manualPortalStatusLabel,
  shipmentActionAvailability,
  type AdminShipment,
  type HazardChoice,
} from "@/features/orders/shipment-actions";
import { ApiError } from "@/lib/api-client";
import { formatToman, toPersianDigits } from "@/lib/utils";
import { shippingAdminService, type PackedQuoteOption } from "@/services/shipping";
import { ordersKeys } from "@/features/orders/queries";
import type { OrderDetail } from "@/types/order";

type PackageFormState = {
  length_cm: string;
  width_cm: string;
  height_cm: string;
  weight_grams: string;
  is_fragile: HazardChoice;
  is_liquid: HazardChoice;
};

const EMPTY_PACKAGE_FORM: PackageFormState = {
  length_cm: "",
  width_cm: "",
  height_cm: "",
  weight_grams: "",
  is_fragile: null,
  is_liquid: null,
};

function ManualPortalWorkflow({
  shipment,
  orderId,
  pending,
  onRegister,
  onHandoff,
  onDeliver,
  onRequestCorrect,
  actions,
}: {
  shipment: AdminShipment;
  orderId: number;
  pending: boolean;
  onRegister: (body: {
    tracking_code: string;
    provider_parcel_no?: string;
    carrier_code?: string;
    service_code?: string;
    internal_note?: string;
  }) => Promise<void>;
  onHandoff: () => Promise<void>;
  onDeliver: () => Promise<void>;
  onRequestCorrect: (body: { tracking_code: string; provider_parcel_no?: string }) => void;
  actions: ReturnType<typeof shipmentActionAvailability>;
}) {
  const [tracking, setTracking] = useState("");
  const [parcelNo, setParcelNo] = useState("");
  const [carrier, setCarrier] = useState("");
  const [service, setService] = useState("");
  const [note, setNote] = useState("");
  const statusHint = manualPortalStatusLabel(shipment);

  return (
    <div className="grid gap-3 text-sm">
      {statusHint && (
        <p className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 font-medium">
          {statusHint}
        </p>
      )}
      <p className="text-xs text-muted-foreground">
        پس از ثبت مرسوله در پنل پستکس، کد رهگیری را اینجا وارد کنید. هیچ تماس API با پستکس انجام
        نمی‌شود.
      </p>
      {actions.canManualRegister && (
        <div className="grid gap-2 rounded-lg border border-dashed p-3">
          <label className="grid gap-1 text-xs">
            کد رهگیری (الزامی)
            <input
              className="rounded-md border px-2 py-1 tnum"
              value={tracking}
              onChange={(e) => setTracking(e.target.value)}
              minLength={10}
            />
          </label>
          <label className="grid gap-1 text-xs">
            شماره مرسوله پستکس (اختیاری)
            <input
              className="rounded-md border px-2 py-1 tnum"
              value={parcelNo}
              onChange={(e) => setParcelNo(e.target.value)}
            />
          </label>
          <label className="grid gap-1 text-xs">
            حامل (اختیاری)
            <input
              className="rounded-md border px-2 py-1"
              value={carrier}
              onChange={(e) => setCarrier(e.target.value)}
            />
          </label>
          <label className="grid gap-1 text-xs">
            سرویس (اختیاری)
            <input
              className="rounded-md border px-2 py-1"
              value={service}
              onChange={(e) => setService(e.target.value)}
            />
          </label>
          <label className="grid gap-1 text-xs">
            یادداشت داخلی (اختیاری)
            <textarea
              className="rounded-md border px-2 py-1"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={2}
            />
          </label>
          <Button
            size="sm"
            disabled={pending || tracking.trim().length < 10}
            onClick={() =>
              void onRegister({
                tracking_code: tracking.trim(),
                provider_parcel_no: parcelNo.trim() || undefined,
                carrier_code: carrier.trim() || undefined,
                service_code: service.trim() || undefined,
                internal_note: note.trim() || undefined,
              })
            }
          >
            ثبت اطلاعات مرسوله پستکس
          </Button>
        </div>
      )}
      {actions.canManualHandoff && (
        <Button size="sm" variant="secondary" disabled={pending} onClick={() => void onHandoff()}>
          تأیید تحویل فیزیکی به پست
        </Button>
      )}
      {actions.canManualDeliver && (
        <Button size="sm" variant="secondary" disabled={pending} onClick={() => void onDeliver()}>
          تأیید تحویل به مشتری
        </Button>
      )}
      {actions.canManualCorrect && (
        <div className="grid gap-2 rounded-lg border border-dashed p-3">
          <p className="text-xs text-muted-foreground">اصلاح ثبت قبل از تحویل فیزیکی به پست</p>
          <label className="grid gap-1 text-xs">
            کد رهگیری
            <input
              className="rounded-md border px-2 py-1 tnum"
              defaultValue={shipment.tracking_code ?? ""}
              minLength={10}
              id={`mp-correct-${orderId}-${shipment.internal_id}`}
            />
          </label>
          <Button
            size="sm"
            variant="outline"
            disabled={pending}
            onClick={() => {
              const input = document.getElementById(
                `mp-correct-${orderId}-${shipment.internal_id}`,
              ) as HTMLInputElement | null;
              const code = input?.value.trim() ?? "";
              if (code.length < 10) {
                toast.error("کد رهگیری باید حداقل ۱۰ رقم باشد.");
                return;
              }
              void onRequestCorrect({
                tracking_code: code,
                provider_parcel_no: shipment.provider_parcel_no ?? undefined,
              });
            }}
          >
            ذخیره اصلاح (نیاز به PIN)
          </Button>
        </div>
      )}
    </div>
  );
}

function ReceiverWorkflow({ shipment }: { shipment: AdminShipment }) {
  const packaged =
    (shipment.package?.length_cm ?? 0) > 0 && (shipment.package?.weight_grams ?? 0) > 0;
  const quoted = Boolean(shipment.package?.provider_box_type_id || shipment.provider_quoted_at);
  const selected = Boolean(shipment.carrier_code && shipment.service_code);
  const readyToBook = shipment.status === "ready_to_book";
  const booked = Boolean(shipment.provider_parcel_no);
  const ready = shipment.status === "ready_for_pickup" || Boolean(shipment.ready_to_accept);
  const tracking = Boolean(shipment.tracking_code);
  const steps = [
    { label: "در انتظار بسته‌بندی", done: true },
    { label: "ثبت وزن و ابعاد نهایی", done: packaged },
    { label: "دریافت نرخ/سرویس پستکس", done: quoted },
    { label: "انتخاب سرویس", done: selected },
    { label: "آماده ثبت مرسوله", done: readyToBook || booked },
    { label: "ثبت مرسوله", done: booked },
    { label: "آماده تحویل", done: ready },
    { label: "رهگیری", done: tracking },
  ];
  return (
    <ol className="grid gap-1 text-xs text-muted-foreground">
      {steps.map((step, idx) => (
        <li key={step.label} className={step.done ? "text-foreground font-medium" : undefined}>
          {toPersianDigits(idx + 1)}. {step.label}
          {step.done ? " ✓" : ""}
        </li>
      ))}
    </ol>
  );
}

function HazardSelect({
  label,
  value,
  onChange,
}: {
  label: string;
  value: HazardChoice;
  onChange: (next: HazardChoice) => void;
}) {
  return (
    <fieldset className="grid gap-1 text-xs">
      <legend>{label} (الزامی)</legend>
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          size="sm"
          variant={value === true ? "default" : "outline"}
          onClick={() => onChange(true)}
        >
          بله
        </Button>
        <Button
          type="button"
          size="sm"
          variant={value === false ? "default" : "outline"}
          onClick={() => onChange(false)}
        >
          خیر
        </Button>
        {value === null && <span className="self-center text-muted-foreground">بررسی نشده</span>}
      </div>
    </fieldset>
  );
}

function ShipmentPackageForm({
  form,
  pending,
  onChange,
  onSubmit,
}: {
  form: PackageFormState;
  pending: boolean;
  onChange: (next: PackageFormState) => void;
  onSubmit: () => void;
}) {
  return (
    <div className="grid gap-2 rounded-lg border border-dashed border-border/80 p-3 sm:grid-cols-2">
      <p className="sm:col-span-2 text-xs text-muted-foreground">
        ابعاد و وزن نهایی مرسوله بسته‌بندی‌شده (نه مشخصات کاتالوگ کالا)
      </p>
      {(
        [
          ["length_cm", "طول (cm)"],
          ["width_cm", "عرض (cm)"],
          ["height_cm", "ارتفاع (cm)"],
          ["weight_grams", "وزن (g)"],
        ] as const
      ).map(([key, label]) => (
        <label key={key} className="grid gap-1 text-xs">
          {label}
          <input
            className="rounded-md border px-2 py-1 tnum"
            inputMode="numeric"
            value={form[key]}
            onChange={(e) => onChange({ ...form, [key]: e.target.value })}
          />
        </label>
      ))}
      <HazardSelect
        label="شکننده"
        value={form.is_fragile}
        onChange={(next) => onChange({ ...form, is_fragile: next })}
      />
      <HazardSelect
        label="مایع"
        value={form.is_liquid}
        onChange={(next) => onChange({ ...form, is_liquid: next })}
      />
      <Button size="sm" className="sm:col-span-2" disabled={pending} onClick={onSubmit}>
        ثبت وزن و ابعاد نهایی
      </Button>
    </div>
  );
}

export function OrderLogisticsSection({ order }: { order: OrderDetail }) {
  const queryClient = useQueryClient();
  const { data: shipments = order.shipments ?? [] } = useQuery({
    queryKey: ["order-shipments", order.id],
    queryFn: () => shippingAdminService.list(order.id),
    enabled: Boolean(order.shipping_provider || (order.shipments && order.shipments.length)),
  });
  const [cancelId, setCancelId] = useState<number | null>(null);
  const [correctRequest, setCorrectRequest] = useState<{
    shipmentId: number;
    body: { tracking_code: string; provider_parcel_no?: string };
  } | null>(null);
  const [pending, setPending] = useState(false);
  const [packageForms, setPackageForms] = useState<Record<number, PackageFormState>>({});
  const [quoteOptions, setQuoteOptions] = useState<Record<number, PackedQuoteOption[]>>({});

  if (!order.shipping_provider && shipments.length === 0) {
    return null;
  }

  const receiverDue = order.shipping_payment_mode === "receiver_due";
  const fulfillment = receiverDue
    ? receiverFulfillmentDisplay(order, shipments)
    : {
        carrierCode: order.shipping_carrier_code ?? null,
        serviceCode: order.shipping_service_code ?? null,
        providerQuotedCost: order.shipping_provider_quoted_cost ?? null,
      };

  function formFor(shipmentId: number): PackageFormState {
    return packageForms[shipmentId] ?? EMPTY_PACKAGE_FORM;
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
          {receiverDue && (
            <p className="rounded-lg bg-secondary/60 px-3 py-2 text-sm font-medium">
              کرایه: پرداخت توسط گیرنده (پس‌کرایه)
            </p>
          )}
          <p>
            <span className="text-muted-foreground">سرویس: </span>
            {fulfillment.carrierCode ?? "—"} {fulfillment.serviceCode ?? ""}
          </p>
          <p>
            <span className="text-muted-foreground">هزینه مشتری: </span>
            <span className="tnum">
              {receiverDue ? "پس‌کرایه (از گیرنده)" : formatToman(order.shipping_customer_cost)}
            </span>
          </p>
          <p>
            <span className="text-muted-foreground">
              {receiverDue ? "کرایه برآوردی پستکس — پرداخت توسط گیرنده: " : "هزینه کل ارائه‌دهنده به کارزار: "}
            </span>
            <span className="tnum">
              {fulfillment.providerQuotedCost != null
                ? formatToman(fulfillment.providerQuotedCost)
                : "—"}
            </span>
          </p>
        </div>

        {shipments.map((shipment) => {
          const actions = shipmentActionAvailability(shipment);
          const manualPortal = shipment.fulfillment_mode === "manual_portal";
          const options = quoteOptions[shipment.internal_id] ?? [];
          const form = formFor(shipment.internal_id);
          const portalLabel = manualPortalStatusLabel(shipment);
          return (
            <div key={shipment.internal_id} className="space-y-3 rounded-xl border border-border/60 p-4">
              <div className="flex flex-wrap gap-2 text-sm">
                <span className="font-bold">{portalLabel ?? shipment.status_label}</span>
                {shipment.shipping_payment_mode === "receiver_due" && (
                  <span className="rounded-md bg-secondary px-2 py-0.5 text-xs">پس‌کرایه</span>
                )}
                {shipment.provider_parcel_no && (
                  <span className="tnum">Parcel {toPersianDigits(shipment.provider_parcel_no)}</span>
                )}
                {shipment.tracking_code && (
                  <span className="tnum">رهگیری {toPersianDigits(shipment.tracking_code)}</span>
                )}
              </div>
              {manualPortal && shipment.shipping_payment_mode === "receiver_due" ? (
                <ManualPortalWorkflow
                  shipment={shipment}
                  orderId={order.id}
                  pending={pending}
                  actions={actions}
                  onRegister={async (body) =>
                    run("اطلاعات مرسوله ثبت شد", () =>
                      shippingAdminService.manualPortalRegister(order.id, shipment.internal_id, body),
                    )
                  }
                  onHandoff={async () =>
                    run("تحویل به پست ثبت شد", () =>
                      shippingAdminService.manualPortalHandoff(order.id, shipment.internal_id),
                    )
                  }
                  onDeliver={async () =>
                    run("تحویل مشتری ثبت شد", () =>
                      shippingAdminService.manualPortalDeliver(order.id, shipment.internal_id),
                    )
                  }
                  onRequestCorrect={(body) =>
                    setCorrectRequest({ shipmentId: shipment.internal_id, body })
                  }
                />
              ) : (
                shipment.shipping_payment_mode === "receiver_due" && (
                  <ReceiverWorkflow shipment={shipment} />
                )
              )}
              {!manualPortal && shipment.package && (
                <p className="text-xs text-muted-foreground tnum">
                  بسته {toPersianDigits(shipment.package.length_cm)}×{toPersianDigits(shipment.package.width_cm)}×
                  {toPersianDigits(shipment.package.height_cm)} cm / {toPersianDigits(shipment.package.weight_grams)}{" "}
                  g
                  {shipment.package.is_fragile != null
                    ? ` · شکننده: ${shipment.package.is_fragile ? "بله" : "خیر"}`
                    : ""}
                  {shipment.package.is_liquid != null
                    ? ` · مایع: ${shipment.package.is_liquid ? "بله" : "خیر"}`
                    : ""}
                </p>
              )}
              {shipment.last_error_message && (
                <p className="text-xs text-destructive">{shipment.last_error_message}</p>
              )}
              {actions.canSetPackage && (
                <ShipmentPackageForm
                  form={form}
                  pending={pending}
                  onChange={(next) =>
                    setPackageForms((prev) => ({ ...prev, [shipment.internal_id]: next }))
                  }
                  onSubmit={() => {
                    const length = Number(form.length_cm);
                    const width = Number(form.width_cm);
                    const height = Number(form.height_cm);
                    const weight = Number(form.weight_grams);
                    if ([length, width, height, weight].some((v) => !Number.isFinite(v) || v <= 0)) {
                      toast.error("ابعاد و وزن باید بزرگ‌تر از صفر باشند.");
                      return;
                    }
                    if (!canSubmitFinalPackageHazards(form.is_fragile, form.is_liquid)) {
                      toast.error("وضعیت شکننده و مایع باید صریحاً بله یا خیر انتخاب شود.");
                      return;
                    }
                    void run("بسته نهایی ثبت شد", () =>
                      shippingAdminService.setFinalPackage(order.id, shipment.internal_id, {
                        length_cm: length,
                        width_cm: width,
                        height_cm: height,
                        weight_grams: weight,
                        is_fragile: form.is_fragile === true,
                        is_liquid: form.is_liquid === true,
                      }),
                    );
                  }}
                />
              )}
              {options.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-medium">انتخاب سرویس پستکس</p>
                  {options.map((opt) => (
                    <Button
                      key={`${opt.carrier_code}:${opt.service_code}`}
                      size="sm"
                      variant="outline"
                      disabled={pending}
                      className="me-2"
                      onClick={() =>
                        void run("سرویس انتخاب شد", () =>
                          shippingAdminService.selectService(order.id, shipment.internal_id, {
                            carrier_code: opt.carrier_code,
                            service_code: opt.service_code,
                          }),
                        )
                      }
                    >
                      {opt.service_name || `${opt.carrier_code}/${opt.service_code}`} ·{" "}
                      {formatToman(opt.provider_amount_toman)} (اطلاعاتی)
                    </Button>
                  ))}
                </div>
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
                {actions.canPackedQuote && (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={pending}
                    onClick={() =>
                      void run("نرخ پس‌کرایه دریافت شد", async () => {
                        const result = await shippingAdminService.packedQuote(
                          order.id,
                          shipment.internal_id,
                        );
                        setQuoteOptions((prev) => ({
                          ...prev,
                          [shipment.internal_id]: result.options,
                        }));
                      })
                    }
                  >
                    دریافت نرخ پستکس
                  </Button>
                )}
                {actions.canScheduleBooking && (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={pending}
                    onClick={() =>
                      void run("آماده ثبت شد", () =>
                        shippingAdminService.scheduleBooking(order.id, shipment.internal_id),
                      )
                    }
                  >
                    آماده ثبت مرسوله
                  </Button>
                )}
                {(actions.canBook || actions.canRetrySafe) && (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={pending}
                    onClick={() =>
                      void run("ثبت مرسوله انجام شد", () =>
                        shippingAdminService.book(order.id, shipment.internal_id),
                      )
                    }
                  >
                    ثبت مرسوله در پستکس
                  </Button>
                )}
                {actions.canReady && (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={pending}
                    onClick={() =>
                      void run("آماده جمع‌آوری شد", () =>
                        shippingAdminService.markReady(order.id, shipment.internal_id),
                      )
                    }
                  >
                    آماده جمع‌آوری
                  </Button>
                )}
                {actions.canLabel && (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={pending}
                    onClick={() =>
                      void run("برچسب دریافت شد", () =>
                        shippingAdminService.downloadLabel(order.id, shipment.internal_id),
                      )
                    }
                  >
                    دانلود برچسب
                  </Button>
                )}
                {actions.canRefresh && (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={pending}
                    onClick={() =>
                      void run("رهگیری به‌روز شد", () =>
                        shippingAdminService.refreshTracking(order.id, shipment.internal_id),
                      )
                    }
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
                          address_line:
                            typeof shipping.address_line === "string" ? shipping.address_line : null,
                          postal_code:
                            typeof shipping.postal_code === "string" ? shipping.postal_code : null,
                        }),
                      );
                    }}
                  >
                    ویرایش آدرس (قبل از مهلت)
                  </Button>
                )}
                {actions.canCancel && (
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-destructive"
                    onClick={() => setCancelId(shipment.internal_id)}
                  >
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

      <StepUpDialog
        open={correctRequest != null}
        onOpenChange={(open) => {
          if (!open) setCorrectRequest(null);
        }}
        title="اصلاح ثبت دستی مرسوله"
        description="اصلاح کد رهگیری قبل از تحویل فیزیکی به پست نیاز به تأیید PIN دارد."
        actionPending={pending}
        onVerified={async (token) => {
          if (correctRequest == null) return;
          setPending(true);
          try {
            await shippingAdminService.manualPortalCorrect(
              order.id,
              correctRequest.shipmentId,
              correctRequest.body,
              token,
            );
            toast.success("اصلاح ثبت ذخیره شد.");
            setCorrectRequest(null);
            void queryClient.invalidateQueries({ queryKey: ["order-shipments", order.id] });
            void queryClient.invalidateQueries({ queryKey: ordersKeys.detail(order.id) });
          } catch (err) {
            toast.error(err instanceof ApiError ? err.message : "اصلاح ثبت ناموفق بود.");
          } finally {
            setPending(false);
          }
        }}
      />
    </Card>
  );
}
