"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { motion } from "framer-motion";
import { Call, Message, TickSquare } from "react-iconly";
import { Button } from "@/components/ui/button";
import { Field, fieldInputClass, fieldTextareaClass } from "@/components/ui/field";
import { contactSchema, type ContactValues } from "@/lib/validation";
import { useSubmitContact } from "@/features/checkout/queries";
import { STORE_PHONE_DISPLAY, STORE_PHONE_E164 } from "@/lib/store-location";
import { useMotionSafe } from "@/lib/use-motion-safe";

/** Compact contact / ticket form for home — posts to existing /contact API. */
export function HomeContactSection() {
  const motionSafe = useMotionSafe();
  const form = useForm<ContactValues>({
    resolver: zodResolver(contactSchema),
    defaultValues: { subject: "پیام از صفحه اصلی" },
  });
  const submit = useSubmitContact();
  const { errors } = form.formState;

  const onSubmit = form.handleSubmit((values) =>
    submit.mutate(values, { onSuccess: () => form.reset({ subject: "پیام از صفحه اصلی" }) }),
  );

  return (
    <section
      aria-labelledby="home-contact-heading"
      className="overflow-hidden rounded-[1.75rem] border border-border/55 bg-card shadow-soft"
    >
      <div className="grid lg:grid-cols-[0.9fr_1.1fr]">
        <motion.div
          initial={motionSafe ? { opacity: 0, x: 20 } : false}
          whileInView={motionSafe ? { opacity: 1, x: 0 } : undefined}
          viewport={{ once: true, amount: 0.35 }}
          className="relative overflow-hidden bg-[#171918] px-6 py-10 text-white sm:px-8 sm:py-12"
        >
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,rgba(208,35,39,0.35),transparent_55%)]"
          />
          <div className="relative">
            <p className="text-[11px] font-black tracking-[0.18em] text-primary">تیکت و پشتیبانی</p>
            <h2
              id="home-contact-heading"
              className="mt-3 text-2xl font-black tracking-tight sm:text-3xl"
            >
              تماس با ما
            </h2>
            <p className="mt-3 max-w-sm text-sm leading-7 text-white/65">
              سوال، همکاری یا پشتیبانی — پیام بفرست؛ با کد رهگیری پیگیری می‌کنی. پیام‌ها در پنل
              ادمین کارزار ثبت می‌شوند.
            </p>
            <a
              href={`tel:${STORE_PHONE_E164}`}
              className="mt-8 inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-2.5 text-sm font-bold backdrop-blur-md transition hover:bg-white/15"
              dir="ltr"
            >
              <Call size="small" set="bold" />
              {STORE_PHONE_DISPLAY}
            </a>
          </div>
        </motion.div>

        <motion.div
          initial={motionSafe ? { opacity: 0, x: -16 } : false}
          whileInView={motionSafe ? { opacity: 1, x: 0 } : undefined}
          viewport={{ once: true, amount: 0.35 }}
          className="px-6 py-8 sm:px-8 sm:py-10"
        >
          {submit.isSuccess ? (
            <div className="grid min-h-[280px] place-items-center text-center">
              <div>
                <span className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-primary text-white">
                  <TickSquare set="bold" />
                </span>
                <p className="mt-4 text-lg font-black text-foreground">پیام ثبت شد</p>
                <p className="mt-1 text-sm text-steel">
                  کد رهگیری:{" "}
                  <span className="font-bold text-primary" dir="ltr">
                    {submit.data?.ticket}
                  </span>
                </p>
              </div>
            </div>
          ) : (
            <form onSubmit={onSubmit} className="space-y-3.5">
              <div className="grid gap-3.5 sm:grid-cols-2">
                <Field label="نام" error={errors.full_name?.message}>
                  <input className={fieldInputClass} {...form.register("full_name")} />
                </Field>
                <Field label="موبایل" error={errors.phone?.message}>
                  <input className={fieldInputClass} dir="ltr" {...form.register("phone")} />
                </Field>
              </div>
              <Field label="موضوع" error={errors.subject?.message}>
                <input className={fieldInputClass} {...form.register("subject")} />
              </Field>
              <Field label="پیام" error={errors.message?.message}>
                <textarea className={fieldTextareaClass} rows={4} {...form.register("message")} />
              </Field>
              <Button type="submit" className="w-full gap-2" disabled={submit.isPending}>
                <Message size="small" set="bold" />
                {submit.isPending ? "در حال ارسال…" : "ارسال تیکت"}
              </Button>
            </form>
          )}
        </motion.div>
      </div>
    </section>
  );
}
