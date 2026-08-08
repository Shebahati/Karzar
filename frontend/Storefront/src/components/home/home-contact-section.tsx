"use client";

import type { FormEvent } from "react";
import type { FieldErrors, UseFormReturn } from "react-hook-form";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { motion } from "framer-motion";
import { Call, Send, TickSquare } from "react-iconly";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { contactSchema, type ContactValues } from "@/lib/validation";
import { useSubmitContact } from "@/features/checkout/queries";
import { STORE_PHONE_DISPLAY, STORE_PHONE_E164 } from "@/lib/store-location";
import { useMotionSafe } from "@/lib/use-motion-safe";
import { cn } from "@/lib/utils";

/** Soft-fill controls for the dark support surface — match storefront Input (no harsh borders). */
const darkFieldClass =
  "[&>span:first-child]:text-[#F0F0F0] [&>span[role=alert]]:text-[#ff9a9c]";

const darkInputClass =
  "h-12 w-full rounded-xl border-0 bg-white/[0.08] px-4 text-base font-medium text-white outline-none shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] transition-[background-color,box-shadow] placeholder:text-white/45 focus:bg-white/[0.12] focus:ring-2 focus:ring-[#D02327]/40";

const darkTextareaClass =
  "w-full rounded-xl border-0 bg-white/[0.08] p-4 text-base font-medium text-white outline-none shadow-[inset_0_1px_0_rgba(255,255,255,0.06)] transition-[background-color,box-shadow] placeholder:text-white/45 focus:bg-white/[0.12] focus:ring-2 focus:ring-[#D02327]/40";

function ContactIntro() {
  return (
    <>
      <p className="text-[11px] font-black tracking-normal text-[#D02327]">
        کارزار · پشتیبانی
      </p>
      <h2
        id="home-contact-heading"
        className="mt-3 text-2xl font-black tracking-normal text-white sm:text-3xl"
      >
        تیکت و پشتیبانی
      </h2>
      <p className="mt-3 max-w-sm text-sm leading-7 text-white/70">
        سوال، همکاری یا پشتیبانی — پیام بفرستید؛ با کد رهگیری پیگیری می‌کنید.
        پیام‌ها در پنل ادمین کارزار ثبت می‌شوند.
      </p>

      <a
        href={`tel:${STORE_PHONE_E164}`}
        className={cn(
          "mt-8 inline-flex w-fit items-center gap-3 rounded-2xl bg-white/[0.06] px-4 py-3",
          "ring-1 ring-inset ring-white/15 transition",
          "hover:bg-white/[0.1] hover:ring-[#D02327]/40 hover:shadow-[0_12px_28px_-16px_rgba(208,35,39,0.45)]",
        )}
      >
        <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#D02327] text-white">
          <Call size="small" set="bold" />
        </span>
        <span className="text-start">
          <span className="block text-[11px] font-bold text-white/60">
            تماس مستقیم
          </span>
          <span className="mt-0.5 block text-base font-black text-white tnum" dir="ltr">
            {STORE_PHONE_DISPLAY}
          </span>
        </span>
      </a>
    </>
  );
}

function ContactFormBody({
  form,
  submit,
  errors,
  onSubmit,
  motionSafe,
}: {
  form: UseFormReturn<ContactValues>;
  submit: ReturnType<typeof useSubmitContact>;
  errors: FieldErrors<ContactValues>;
  onSubmit: (e?: FormEvent) => Promise<void>;
  motionSafe: boolean;
}) {
  if (submit.isSuccess) {
    return (
      <div className="flex min-h-[280px] flex-col items-center justify-center rounded-2xl bg-white/[0.06] px-5 py-10 text-center ring-1 ring-inset ring-white/12">
        {motionSafe ? (
          <motion.span
            initial={{ scale: 0.85, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="grid h-14 w-14 place-items-center rounded-full bg-[#D02327] text-white shadow-[0_12px_32px_rgba(208,35,39,0.4)]"
          >
            <TickSquare set="bold" />
          </motion.span>
        ) : (
          <span className="grid h-14 w-14 place-items-center rounded-full bg-[#D02327] text-white shadow-[0_12px_32px_rgba(208,35,39,0.4)]">
            <TickSquare set="bold" />
          </span>
        )}
        <p className="mt-4 text-lg font-black text-white">پیام ثبت شد</p>
        <p className="mt-1.5 text-sm text-white/70">
          کد رهگیری:{" "}
          <span className="font-black text-[#ff9a9c] tnum" dir="ltr">
            {submit.data?.ticket}
          </span>
        </p>
        <div className="mt-5 flex flex-wrap justify-center gap-2">
          <Button
            type="button"
            variant="soft"
            size="sm"
            onClick={() => {
              const t = submit.data?.ticket;
              if (t) void navigator.clipboard?.writeText(t);
            }}
          >
            کپی کد
          </Button>
          <Button type="button" variant="soft" size="sm" onClick={() => submit.reset()}>
            ارسال پیام جدید
          </Button>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} className="space-y-3.5" noValidate>
      {submit.isError ? (
        <p
          className="rounded-xl bg-[#D02327]/15 px-3 py-2.5 text-sm font-bold text-[#ff9a9c] ring-1 ring-inset ring-[#D02327]/30"
          role="alert"
        >
          ارسال پیام ناموفق بود. دوباره تلاش کنید.
        </p>
      ) : null}

      <div className="grid gap-3.5 sm:grid-cols-2">
        <Field label="نام" error={errors.full_name?.message} className={darkFieldClass}>
          <input
            className={darkInputClass}
            autoComplete="name"
            {...form.register("full_name")}
          />
        </Field>
        <Field label="موبایل" error={errors.phone?.message} className={darkFieldClass}>
          <input
            className={`${darkInputClass} tnum`}
            dir="ltr"
            inputMode="tel"
            autoComplete="tel"
            placeholder="09XXXXXXXXX"
            {...form.register("phone")}
          />
        </Field>
      </div>
      <Field label="موضوع" error={errors.subject?.message} className={darkFieldClass}>
        <input
          className={darkInputClass}
          placeholder="مثلاً: پیگیری سفارش، سوال فنی…"
          {...form.register("subject")}
        />
      </Field>
      <Field label="پیام" error={errors.message?.message} className={darkFieldClass}>
        <textarea
          className={darkTextareaClass}
          rows={4}
          placeholder="شرح مشکل یا درخواست خود را بنویسید…"
          {...form.register("message")}
        />
      </Field>
      <Button
        type="submit"
        size="lg"
        className="w-full gap-2 bg-[#D02327] hover-fine:bg-[#b81e23]"
        disabled={submit.isPending}
      >
        <Send size="small" set="bold" />
        {submit.isPending ? "در حال ارسال…" : "ارسال تیکت"}
      </Button>
    </form>
  );
}

/** Home support strip — same ContactRequest fields as POST /contact (OpenAPI). */
export function HomeContactSection() {
  const motionSafe = useMotionSafe();
  const form = useForm<ContactValues>({
    resolver: zodResolver(contactSchema),
  });
  const submit = useSubmitContact();
  const { errors } = form.formState;

  const onSubmit = form.handleSubmit((values) =>
    submit.mutate(values, {
      onSuccess: () => form.reset(),
    }),
  );

  return (
    <section
      aria-labelledby="home-contact-heading"
      className="relative overflow-hidden rounded-[1.75rem] text-white"
    >
      {/* Atmospheric wash — deep charcoal / steel + restrained brand red */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-gradient-to-bl from-[#1a1b1c] via-[#121314] to-[#0e0f0f]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_100%_0%,rgba(208,35,39,0.22),transparent_55%),radial-gradient(ellipse_70%_50%_at_0%_100%,rgba(94,95,94,0.18),transparent_50%)]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -start-24 top-0 hidden h-64 w-64 rounded-full bg-[#D02327]/[0.12] blur-3xl md:block"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -end-16 bottom-0 hidden h-56 w-56 rounded-full bg-[#5E5F5E]/[0.14] blur-3xl md:block"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-8 top-0 h-px bg-gradient-to-l from-transparent via-[#D02327]/55 to-transparent"
      />

      <div className="relative grid gap-10 px-5 py-10 sm:px-8 sm:py-12 lg:grid-cols-[0.85fr_1.15fr] lg:gap-14 lg:px-10 lg:py-14">
        {motionSafe ? (
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.35 }}
            transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
            className="flex flex-col justify-center"
          >
            <ContactIntro />
          </motion.div>
        ) : (
          <div className="flex flex-col justify-center">
            <ContactIntro />
          </div>
        )}

        {motionSafe ? (
          <motion.div
            initial={{ opacity: 0, y: 22 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ duration: 0.55, delay: 0.08, ease: [0.22, 1, 0.36, 1] }}
            className="min-w-0"
          >
            <ContactFormBody
              form={form}
              submit={submit}
              errors={errors}
              onSubmit={onSubmit}
              motionSafe
            />
          </motion.div>
        ) : (
          <div className="min-w-0">
            <ContactFormBody
              form={form}
              submit={submit}
              errors={errors}
              onSubmit={onSubmit}
              motionSafe={false}
            />
          </div>
        )}
      </div>
    </section>
  );
}
