"use client";

import { useState } from "react";
import { Lock, ShieldDone } from "react-iconly";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { useVerifyPin } from "@/features/catalog/queries";
import { ApiError } from "@/lib/api-client";
import { stepUpPinSchema } from "@/lib/validation";

interface StepUpDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Invoked with the short-lived step-up token after a correct PIN. */
  onVerified: (stepUpToken: string) => void;
  title?: string;
  description?: string;
  /** True while the guarded action runs after verification. */
  actionPending?: boolean;
}

/**
 * Step-up authentication gate. Exchanges a static admin PIN for a short-lived
 * token via the catalog service, then hands the token to `onVerified` so the
 * caller can execute the sensitive action (e.g. delete).
 */
export function StepUpDialog({
  open,
  onOpenChange,
  onVerified,
  title = "تأیید هویت مرحله‌دوم",
  description = "این عملیات حساس است. برای ادامه، کد امنیتی (PIN) مدیر را وارد کنید.",
  actionPending = false,
}: StepUpDialogProps) {
  const [pin, setPin] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [prevOpen, setPrevOpen] = useState(open);
  const verifyPin = useVerifyPin();

  // Reset transient state whenever the dialog toggles (adjust-state-on-render
  // pattern — avoids a cascading-render effect).
  if (open !== prevOpen) {
    setPrevOpen(open);
    setPin("");
    setError(null);
  }

  const submitting = verifyPin.isPending || actionPending;

  async function handleConfirm() {
    setError(null);
    const parsed = stepUpPinSchema.safeParse(pin);
    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message ?? "کد امنیتی نامعتبر است.");
      return;
    }
    try {
      const { secure_token } = await verifyPin.mutateAsync(parsed.data);
      onVerified(secure_token);
    } catch (err) {
      if (err instanceof ApiError && err.code === "RATE_LIMITED") {
        const wait = err.retryAfterSeconds ?? 30;
        setError(`تعداد تلاش زیاد است. ${wait} ثانیه صبر کنید و دوباره تلاش کنید.`);
        return;
      }
      const message =
        err instanceof ApiError
          ? (err.fieldErrors.pin ?? err.message)
          : "تأیید کد امنیتی ناموفق بود.";
      setError(message);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(next) => (!submitting ? onOpenChange(next) : undefined)}>
      <DialogContent className="max-w-md">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-accent text-primary">
          <ShieldDone set="bulk" size={30} primaryColor="#C22026" />
        </div>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        <Field label="کد امنیتی (PIN)" htmlFor="step-up-pin" error={error ?? undefined}>
          <div className="relative">
            <span className="pointer-events-none absolute inset-y-0 start-3 flex items-center text-muted-foreground">
              <Lock set="light" size={18} />
            </span>
            <Input
              id="step-up-pin"
              type="password"
              inputMode="numeric"
              autoComplete="one-time-code"
              autoFocus
              maxLength={12}
              dir="ltr"
              placeholder="••••••••"
              className="ps-10 text-center tracking-[0.4em]"
              value={pin}
              aria-invalid={Boolean(error)}
              onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))}
              onKeyDown={(e) => {
                if (e.key === "Enter") void handleConfirm();
              }}
              disabled={submitting}
            />
          </div>
        </Field>

        <div className="flex gap-3">
          <Button
            type="button"
            className="flex-1"
            onClick={handleConfirm}
            disabled={submitting}
          >
            {submitting ? "در حال بررسی..." : "تأیید و ادامه"}
          </Button>
          <Button
            type="button"
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={submitting}
          >
            انصراف
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
