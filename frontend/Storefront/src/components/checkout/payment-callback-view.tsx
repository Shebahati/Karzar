"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { CloseSquare, TickSquare } from "react-iconly";
import { Container } from "@/components/ui/container";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { paymentService } from "@/services/payments";
import { orderService } from "@/services/orders";
import {
  clearPendingPayment,
  readPendingPayment,
} from "@/lib/pending-payment";
import { useCartStore } from "@/store/cart-store";

type VerifyState = "loading" | "success" | "failed" | "need_tracking";

export function PaymentCallbackView() {
  const router = useRouter();
  const sp = useSearchParams();
  const clearCart = useCartStore((s) => s.clearCart);
  const [state, setState] = useState<VerifyState>("loading");
  const [message, setMessage] = useState("در حال تأیید پرداخت…");
  const [trackingCode, setTrackingCode] = useState<string | null>(null);
  const [trackingInput, setTrackingInput] = useState("");
  const [recovering, setRecovering] = useState(false);

  const authority = sp.get("Authority") ?? sp.get("authority") ?? "";
  const gatewayStatus = sp.get("Status") ?? sp.get("status") ?? "";

  async function runVerify(pending: { order_id?: number; tracking_code?: string } | null) {
    const result = await paymentService.verify({
      order_id: pending?.order_id,
      authority,
      status: gatewayStatus,
      tracking_code: pending?.tracking_code,
    });

    clearPendingPayment();

    if (result.success) {
      const ref = pending?.tracking_code || result.tracking_code;
      clearCart();
      setState("success");
      setTrackingCode(ref);
      setMessage(result.message);
      try {
        if (ref) await orderService.track(ref);
      } catch {
        /* tracking optional */
      }
      if (ref) {
        router.replace(`/checkout/success?ref=${ref}&mode=purchase&paid=1`);
      }
      return;
    }

    setState("failed");
    setMessage(result.message);
  }

  useEffect(() => {
    if (!authority) {
      setState("failed");
      setMessage("پاسخ درگاه پرداخت نامعتبر است.");
      return;
    }

    const pending = readPendingPayment();
    let cancelled = false;
    (async () => {
      try {
        // Authority alone is enough for the API; pending order_id is optional.
        await runVerify(pending?.order_id ? pending : null);
      } catch {
        if (!cancelled) {
          // Fall back to tracking recovery only when authority verify failed hard.
          if (!pending?.order_id) {
            setState("need_tracking");
            setMessage(
              "تأیید خودکار ناموفق بود. کد پیگیری سفارش را وارد کنید یا با پشتیبانی تماس بگیرید.",
            );
          } else {
            setState("failed");
            setMessage(
              "تأیید پرداخت با خطا مواجه شد. در صورت کسر وجه، با پشتیبانی تماس بگیرید یا کد پیگیری را وارد کنید.",
            );
          }
        }
      }
    })();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- verify once per authority
  }, [authority, gatewayStatus]);

  async function recoverWithTrackingCode() {
    const code = trackingInput.trim();
    if (!code) {
      setMessage("کد پیگیری را وارد کنید.");
      return;
    }
    if (!authority) {
      setState("failed");
      setMessage("پاسخ درگاه پرداخت نامعتبر است.");
      return;
    }

    setRecovering(true);
    try {
      // Confirm tracking code exists publicly; verify is still authority-bound on the server.
      await orderService.track(code);
      setState("loading");
      setMessage("در حال تأیید پرداخت…");
      await runVerify({ tracking_code: code });
    } catch {
      setMessage(
        "بازیابی ناموفق بود. کد پیگیری را بررسی کنید یا با پشتیبانی تماس بگیرید.",
      );
      setState("need_tracking");
    } finally {
      setRecovering(false);
    }
  }

  return (
    <Container className="grid min-h-[70vh] place-items-center py-12">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-lg rounded-3xl bg-card p-8 text-center shadow-elevated sm:p-12"
      >
        {state === "loading" && (
          <>
            <span className="mx-auto grid h-16 w-16 animate-pulse place-items-center rounded-full bg-secondary" />
            <h1 className="mt-6 text-xl font-bold text-foreground">در حال تأیید پرداخت</h1>
            <p className="mt-2 text-sm text-muted-foreground">{message}</p>
          </>
        )}

        {state === "success" && (
          <>
            <span className="mx-auto grid h-16 w-16 place-items-center rounded-full bg-success text-success-foreground">
              <TickSquare set="bold" size="large" />
            </span>
            <h1 className="mt-6 text-xl font-bold text-foreground">پرداخت موفق</h1>
            <p className="mt-2 text-sm text-muted-foreground">{message}</p>
            {trackingCode && (
              <p className="mt-4 text-sm text-muted-foreground">
                کد پیگیری:{" "}
                <span className="font-bold text-primary tnum">{trackingCode}</span>
              </p>
            )}
          </>
        )}

        {state === "need_tracking" && (
          <>
            <span className="mx-auto grid h-16 w-16 place-items-center rounded-full bg-secondary text-foreground">
              <TickSquare set="bold" size="large" />
            </span>
            <h1 className="mt-6 text-xl font-bold text-foreground">بازیابی تأیید پرداخت</h1>
            <p className="mt-2 text-sm text-muted-foreground">{message}</p>
            <div className="mt-6 space-y-3 text-start">
              <Input
                dir="ltr"
                className="text-start tnum"
                placeholder="کد پیگیری سفارش"
                value={trackingInput}
                onChange={(e) => setTrackingInput(e.target.value)}
              />
              <Button
                className="w-full"
                disabled={recovering}
                onClick={() => void recoverWithTrackingCode()}
              >
                {recovering ? "در حال بازیابی…" : "تأیید با کد پیگیری"}
              </Button>
              <Button
                variant="soft"
                className="w-full"
                onClick={() => router.push("/login?next=/account/orders")}
              >
                ورود به حساب و سفارش‌ها
              </Button>
            </div>
          </>
        )}

        {state === "failed" && (
          <>
            <span className="mx-auto grid h-16 w-16 place-items-center rounded-full bg-destructive/10 text-destructive">
              <CloseSquare set="bold" size="large" />
            </span>
            <h1 className="mt-6 text-xl font-bold text-foreground">پرداخت ناموفق</h1>
            <p className="mt-2 text-sm text-muted-foreground">{message}</p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Button
                className="flex-1"
                onClick={() => {
                  setState("need_tracking");
                  setMessage("کد پیگیری سفارش را وارد کنید تا در صورت امکان پرداخت تأیید شود.");
                }}
              >
                بازیابی با کد پیگیری
              </Button>
              <Button variant="soft" className="flex-1" onClick={() => router.push("/account/orders")}>
                سفارش‌های من
              </Button>
            </div>
          </>
        )}
      </motion.div>
    </Container>
  );
}
