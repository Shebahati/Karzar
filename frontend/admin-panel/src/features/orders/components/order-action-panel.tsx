"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { CloseSquare, Delete, Send, TickSquare, Wallet } from "react-iconly";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StepUpDialog } from "@/components/step-up-dialog";
import { ShipOrderDialog } from "@/features/orders/components/ship-order-dialog";
import { QuoteIssueDialog } from "@/features/orders/components/quote-issue-dialog";
import { useArchiveOrder, useUpdateOrderStatus, ordersKeys } from "@/features/orders/queries";
import {
  canCancel,
  getPrimaryAction,
  STATUS_LABELS,
} from "@/features/orders/order-workflow";
import { ApiError } from "@/lib/api-client";
import { paymentsAdminService } from "@/services/payments";
import type { OrderDetail } from "@/types/order";

interface OrderActionPanelProps {
  order: OrderDetail;
}

export function OrderActionPanel({ order }: OrderActionPanelProps) {
  const router = useRouter();
  const updateStatus = useUpdateOrderStatus(order.id);
  const archiveOrder = useArchiveOrder();
  const queryClient = useQueryClient();
  const primary = getPrimaryAction(order);

  const [shipOpen, setShipOpen] = useState(false);
  const [quoteOpen, setQuoteOpen] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [refundOpen, setRefundOpen] = useState(false);
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [actionPending, setActionPending] = useState(false);

  const needsRefundBeforeCancel =
    order.mode === "purchase" &&
    (order.status === "paid" ||
      order.status === "processing" ||
      order.status === "shipped" ||
      order.payment_status === "paid");

  async function advance(nextStatus: NonNullable<typeof primary>["nextStatus"]) {
    if (!nextStatus) return;
    try {
      await updateStatus.mutateAsync({ status: nextStatus });
      toast.success(`مرحله «${STATUS_LABELS[nextStatus]}» ثبت شد.`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "عملیات ناموفق بود.");
    }
  }

  function handlePrimaryClick() {
    if (!primary) return;
    if (primary.type === "ship") {
      setShipOpen(true);
      return;
    }
    if (primary.type === "quote") {
      setQuoteOpen(true);
      return;
    }
    if (primary.nextStatus) void advance(primary.nextStatus);
  }

  const isTerminal =
    order.status === "delivered" ||
    order.status === "inquiry_closed" ||
    order.status === "cancelled";

  return (
    <>
      <Card className="border-primary/10">
        <CardHeader>
          <CardTitle className="text-base">اقدام بعدی</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {isTerminal ? (
            <div className="flex items-center gap-3 rounded-xl bg-success/10 p-4 text-sm">
              <TickSquare set="bold" size={22} primaryColor="#2E9E5B" />
              <p className="font-bold text-foreground">
                {order.status === "cancelled"
                  ? "این پرونده لغو شده و اقدام دیگری لازم نیست."
                  : "گردش کار تکمیل شده است."}
              </p>
            </div>
          ) : primary ? (
            <>
              <p className="text-sm leading-6 text-muted-foreground">{primary.description}</p>
              <Button
                type="button"
                size="lg"
                className="w-full gap-2 sm:w-auto"
                disabled={updateStatus.isPending}
                onClick={handlePrimaryClick}
              >
                <Send set="bold" size={18} primaryColor="#FFFFFF" />
                {primary.label}
              </Button>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">اقدام بعدی برای این وضعیت تعریف نشده است.</p>
          )}

          {needsRefundBeforeCancel && (
            <Button
              type="button"
              variant="outline"
              className="w-full gap-2 sm:w-auto"
              onClick={() => setRefundOpen(true)}
            >
              <Wallet set="light" size={18} />
              استرداد وجه و لغو
            </Button>
          )}

          {canCancel(order) && !needsRefundBeforeCancel && (
            <Button
              type="button"
              variant="outline"
              className="w-full gap-2 border-destructive/30 text-destructive hover:bg-destructive/5 sm:w-auto"
              onClick={() => setCancelOpen(true)}
            >
              <CloseSquare set="light" size={18} primaryColor="#C22026" />
              لغو {order.mode === "inquiry" ? "استعلام" : "سفارش"}
            </Button>
          )}

          {needsRefundBeforeCancel && (
            <p className="text-xs leading-5 text-muted-foreground">
              برای سفارش پرداخت‌شده ابتدا باید از مسیر استرداد (Refund) استفاده کنید؛ لغو مستقیم توسط
              سرور رد می‌شود.
            </p>
          )}

          {isTerminal && (
            <Button
              type="button"
              variant="outline"
              className="w-full gap-2 border-destructive/30 text-destructive hover:bg-destructive/5 sm:w-auto"
              onClick={() => setArchiveOpen(true)}
            >
              <Delete set="light" size={18} primaryColor="currentColor" />
              بایگانی {order.mode === "inquiry" ? "استعلام" : "سفارش"}
            </Button>
          )}
        </CardContent>
      </Card>

      <ShipOrderDialog order={order} open={shipOpen} onOpenChange={setShipOpen} />
      <QuoteIssueDialog order={order} open={quoteOpen} onOpenChange={setQuoteOpen} />

      <StepUpDialog
        open={cancelOpen}
        onOpenChange={setCancelOpen}
        title={`لغو ${order.mode === "inquiry" ? "استعلام" : "سفارش"}`}
        description="این عملیات نیاز به تأیید PIN امنیتی دارد."
        actionPending={actionPending}
        onVerified={async (token) => {
          setActionPending(true);
          try {
            await updateStatus.mutateAsync({ status: "cancelled", stepUpToken: token });
            toast.success("لغو با موفقیت ثبت شد.");
            setCancelOpen(false);
          } catch (err) {
            if (err instanceof ApiError && err.code === "CONFLICT") {
              toast.error("این سفارش نیازمند استرداد قبل از لغو است.");
              setCancelOpen(false);
              setRefundOpen(true);
            } else {
              toast.error(err instanceof ApiError ? err.message : "لغو ناموفق بود.");
            }
          } finally {
            setActionPending(false);
          }
        }}
      />

      <StepUpDialog
        open={refundOpen}
        onOpenChange={setRefundOpen}
        title="استرداد وجه"
        description="پس از تأیید PIN، مبلغ پرداخت‌شده استرداد و سفارش لغو می‌شود."
        actionPending={actionPending}
        onVerified={async (token) => {
          setActionPending(true);
          try {
            await paymentsAdminService.refund(order.id, token);
            toast.success("استرداد و لغو با موفقیت ثبت شد.");
            setRefundOpen(false);
            void queryClient.invalidateQueries({ queryKey: ordersKeys.all });
          } catch (err) {
            toast.error(err instanceof ApiError ? err.message : "استرداد ناموفق بود.");
          } finally {
            setActionPending(false);
          }
        }}
      />

      <StepUpDialog
        open={archiveOpen}
        onOpenChange={setArchiveOpen}
        title={`بایگانی ${order.mode === "inquiry" ? "استعلام" : "سفارش"}`}
        description="این عملیات پرونده را بایگانی (حذف نرم) می‌کند و غیرقابل بازگشت است."
        actionPending={actionPending || archiveOrder.isPending}
        onVerified={async (token) => {
          setActionPending(true);
          try {
            await archiveOrder.mutateAsync({ id: order.id, stepUpToken: token });
            toast.success("پرونده بایگانی شد.");
            setArchiveOpen(false);
            router.push(order.mode === "inquiry" ? "/quotes" : "/orders");
          } catch (err) {
            toast.error(err instanceof ApiError ? err.message : "بایگانی ناموفق بود.");
          } finally {
            setActionPending(false);
          }
        }}
      />
    </>
  );
}
