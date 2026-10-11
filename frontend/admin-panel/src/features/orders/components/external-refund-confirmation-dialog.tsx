"use client";

import { useState } from "react";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";

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
import { StepUpDialog } from "@/components/step-up-dialog";
import { ordersKeys } from "@/features/orders/queries";
import {
  EXTERNAL_REFUND_REFERENCE_MAX_LENGTH,
  externalRefundToastMessage,
} from "@/features/orders/refund-workflow";
import { ApiError } from "@/lib/api-client";
import { paymentsAdminService } from "@/services/payments";

interface ExternalRefundConfirmationDialogProps {
  orderId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ExternalRefundConfirmationDialog({
  orderId,
  open,
  onOpenChange,
}: ExternalRefundConfirmationDialogProps) {
  const queryClient = useQueryClient();
  const [externalReference, setExternalReference] = useState("");
  const [evidenceNote, setEvidenceNote] = useState("");
  const [stepUpOpen, setStepUpOpen] = useState(false);
  const [actionPending, setActionPending] = useState(false);

  function resetForm() {
    setExternalReference("");
    setEvidenceNote("");
  }

  function handleOpenChange(next: boolean) {
    if (!next) {
      resetForm();
      setStepUpOpen(false);
    }
    onOpenChange(next);
  }

  function validateReference(): string | null {
    const ref = externalReference.trim();
    if (ref.length < 3) {
      toast.error("شناسه/مرجع استرداد باید حداقل ۳ کاراکتر باشد.");
      return null;
    }
    if (ref.length > EXTERNAL_REFUND_REFERENCE_MAX_LENGTH) {
      toast.error(`شناسه/مرجع استرداد حداکثر ${EXTERNAL_REFUND_REFERENCE_MAX_LENGTH} کاراکتر است.`);
      return null;
    }
    if (evidenceNote.trim().length > 500) {
      toast.error("توضیح اپراتور حداکثر ۵۰۰ کاراکتر است.");
      return null;
    }
    return ref;
  }

  function handleContinue() {
    if (!validateReference()) return;
    setStepUpOpen(true);
  }

  return (
    <>
      <Dialog open={open} onOpenChange={handleOpenChange}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>ثبت استرداد انجام‌شده و لغو سفارش</DialogTitle>
            <DialogDescription className="leading-6">
              ابتدا استرداد وجه را در کانال رسمی درگاه/بانک انجام دهید. پس از دریافت شناسه یا مدرک
              استرداد، آن را اینجا ثبت کنید تا وضعیت پرداخت و سفارش در کارزار به‌روزرسانی شود.
            </DialogDescription>
          </DialogHeader>

          <p className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-sm leading-6 text-foreground">
            این فرم وجهی را جابه‌جا نمی‌کند. فقط استردادی را ثبت کنید که قبلاً در کانال رسمی پرداخت
            انجام و تأیید شده است.
          </p>

          <div className="flex flex-col gap-4">
            <Field label="شناسه/مرجع استرداد" required>
              <Input
                value={externalReference}
                onChange={(e) => setExternalReference(e.target.value)}
                placeholder="مثلاً شماره پیگیری بانک یا مرجع رسمی"
                maxLength={EXTERNAL_REFUND_REFERENCE_MAX_LENGTH}
                autoComplete="off"
              />
            </Field>
            <Field label="توضیح/مدرک اپراتور">
              <Textarea
                value={evidenceNote}
                onChange={(e) => setEvidenceNote(e.target.value)}
                rows={3}
                placeholder="اختیاری — خلاصه مدرک یا یادداشت داخلی"
              />
            </Field>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => handleOpenChange(false)}>
              انصراف
            </Button>
            <Button type="button" onClick={handleContinue}>
              ادامه و تأیید PIN
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <StepUpDialog
        open={stepUpOpen}
        onOpenChange={setStepUpOpen}
        title="ثبت استرداد تأییدشده"
        description="پس از تأیید PIN، استرداد خارجی ثبت و در صورت امکان سفارش لغو می‌شود."
        actionPending={actionPending}
        onVerified={async (token) => {
          const ref = validateReference();
          if (!ref) return;
          setActionPending(true);
          try {
            const result = await paymentsAdminService.confirmExternalRefund(
              {
                order_id: orderId,
                external_reference: ref,
                evidence_note: evidenceNote.trim() || undefined,
              },
              token,
            );
            const toastKind = externalRefundToastMessage(result);
            if (toastKind === "success") {
              toast.success("استرداد تأییدشده ثبت و سفارش لغو شد.");
            } else {
              toast.warning(
                "استرداد ثبت شد، اما لغو سفارش کامل نشد و نیاز به بررسی اپراتور دارد.",
              );
            }
            setStepUpOpen(false);
            handleOpenChange(false);
            void queryClient.invalidateQueries({ queryKey: ordersKeys.all });
          } catch (err) {
            toast.error(err instanceof ApiError ? err.message : "ثبت استرداد ناموفق بود.");
          } finally {
            setActionPending(false);
          }
        }}
      />
    </>
  );
}
