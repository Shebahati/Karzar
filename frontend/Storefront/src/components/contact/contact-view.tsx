"use client";

/**
 * Contact — calm Karzar composition
 * ---------------------------------
 * One clear layout: brand signal → channels → form, with a soft map that
 * supports (does not dominate). Comfortable spacing over fold-packing.
 * Soft short-viewport padding only — no height locks, no hidden map.
 */

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { motion } from "framer-motion";
import { Call, Location, Message, Send, TickSquare } from "react-iconly";
import { Container } from "@/components/ui/container";
import { Button } from "@/components/ui/button";
import { Field, fieldInputClass, fieldTextareaClass } from "@/components/ui/field";
import { NeshanDirectionsButton } from "@/components/contact/neshan-directions-button";
import { NeshanMapEmbed } from "@/components/contact/neshan-map-embed";
import { StoreSocialLinks } from "@/components/social/store-social-links";
import { contactSchema, type ContactValues } from "@/lib/validation";
import { useSubmitContact } from "@/features/checkout/queries";
import {
  STORE_ADDRESS_FA,
  STORE_EMAIL,
  STORE_MAPS_URL,
  STORE_NAME_FA,
  STORE_PHONE_DISPLAY,
  STORE_PHONE_E164,
} from "@/lib/store-location";
import { cn } from "@/lib/utils";

const DETAILS = [
  {
    Icon: Call,
    label: "تماس تلفنی",
    value: STORE_PHONE_DISPLAY,
    href: `tel:${STORE_PHONE_E164}`,
    dir: "ltr" as const,
  },
  {
    Icon: Message,
    label: "ایمیل پشتیبانی",
    value: STORE_EMAIL,
    href: `mailto:${STORE_EMAIL}`,
    dir: "ltr" as const,
  },
  {
    Icon: Location,
    label: "نشانی فروشگاه",
    value: STORE_ADDRESS_FA,
    href: STORE_MAPS_URL,
    external: true,
    dir: undefined as "ltr" | undefined,
  },
];

const fade = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
};

export function ContactView() {
  const form = useForm<ContactValues>({ resolver: zodResolver(contactSchema) });
  const submit = useSubmitContact();
  const { errors } = form.formState;

  const onSubmit = form.handleSubmit((values) =>
    submit.mutate(values, { onSuccess: () => form.reset() }),
  );

  return (
    <div className="relative w-full max-w-full overflow-x-clip bg-background">
      {/* Soft atmosphere — one red whisper, one steel wash. No grid chrome. */}
      <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -start-[18%] -top-[22%] h-[28rem] w-[36rem] rounded-full bg-[radial-gradient(closest-side,rgba(208,35,39,0.06),transparent_72%)]" />
        <div className="absolute -bottom-[18%] -end-[12%] h-[24rem] w-[30rem] rounded-full bg-[radial-gradient(closest-side,rgba(94,95,94,0.07),transparent_70%)]" />
      </div>

      <Container
        className={cn(
          "relative py-8 sm:py-10 lg:py-12",
          /* Gentle short-monitor step — beauty over stuffing */
          "[@media(max-height:720px)]:lg:py-8",
        )}
      >
        <motion.header
          {...fade}
          transition={{ duration: 0.45 }}
          className="mx-auto max-w-2xl text-center lg:mx-0 lg:max-w-none lg:text-start"
        >
          <p className="text-[11px] font-bold tracking-[0.2em] text-primary">
            {STORE_NAME_FA}
          </p>
          <h1 className="mt-2.5 text-2xl font-black tracking-tight text-foreground sm:text-[1.75rem]">
            تماس با ما
          </h1>
          <p className="mt-3 text-sm leading-7 text-muted-foreground sm:text-[15px] sm:leading-7">
            سوال، مشاوره یا همکاری — از راه‌های زیر پیام بفرستید؛ سریع پاسخ
            می‌دهیم.
          </p>
        </motion.header>

        <div className="mt-8 grid min-w-0 gap-8 lg:mt-10 lg:grid-cols-2 lg:items-start lg:gap-10 [@media(max-height:720px)]:lg:mt-8 [@media(max-height:720px)]:lg:gap-8">
          {/* Info — open column, not a heavy card stack */}
          <motion.aside
            {...fade}
            transition={{ duration: 0.45, delay: 0.06 }}
            className="flex min-w-0 flex-col gap-7"
          >
            <div id="store-address" className="scroll-mt-24 space-y-1">
              {DETAILS.map(({ Icon, label, value, href, external, dir }) => (
                <a
                  key={label}
                  href={href}
                  {...(external
                    ? { target: "_blank", rel: "noopener noreferrer" }
                    : {})}
                  className={cn(
                    "group flex min-w-0 items-start gap-3.5 rounded-2xl px-3 py-3.5",
                    "transition-colors hover:bg-white/70",
                  )}
                >
                  <span className="mt-0.5 grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-primary/[0.08] text-primary transition-transform duration-300 group-hover:scale-[1.03]">
                    <Icon set="bold" size="small" primaryColor="#D02327" />
                  </span>
                  <div className="min-w-0 flex-1 pt-0.5">
                    <p className="text-xs font-medium text-muted-foreground">
                      {label}
                    </p>
                    <p
                      className="mt-1 break-words text-[15px] font-bold leading-6 text-foreground"
                      dir={dir}
                    >
                      {value}
                    </p>
                  </div>
                </a>
              ))}
            </div>

            <div>
              <p
                id="contact-social-heading"
                className="mb-3 text-xs font-bold text-muted-foreground"
              >
                پیام‌رسان‌ها
              </p>
              <StoreSocialLinks
                tone="light"
                variant="pills"
                labelledBy="contact-social-heading"
              />
            </div>

            <section
              aria-labelledby="store-map-heading"
              className="overflow-hidden rounded-2xl bg-card ring-1 ring-inset ring-border/70"
            >
              <div className="flex flex-col gap-3 border-b border-border/60 px-4 py-3.5 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <h2
                    id="store-map-heading"
                    className="text-sm font-bold text-foreground"
                  >
                    موقعیت روی نقشه
                  </h2>
                  <p className="mt-0.5 text-xs leading-5 text-muted-foreground">
                    پاساژ فجر، پلاک ۱۰۸ · نشان
                  </p>
                </div>
                <NeshanDirectionsButton size="sm" className="w-full shrink-0 sm:w-auto" />
              </div>
              <NeshanMapEmbed className="rounded-none ring-0" />
            </section>
          </motion.aside>

          {/* Form — quiet white panel */}
          <motion.div
            {...fade}
            transition={{ duration: 0.45, delay: 0.1 }}
            className={cn(
              "min-w-0 rounded-[1.25rem] bg-card p-6 sm:p-7",
              "shadow-[0_18px_40px_-28px_rgba(40,48,56,0.28)]",
              "ring-1 ring-inset ring-border/80",
            )}
          >
            <div className="mb-5">
              <h2 className="text-base font-black text-foreground">ارسال پیام</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                تیکت در پنل پشتیبانی کارزار ثبت می‌شود.
              </p>
            </div>

            {submit.isSuccess ? (
              <div className="grid min-h-[18rem] place-items-center py-8 text-center">
                <div>
                  <span className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-primary/10 text-primary">
                    <TickSquare set="bold" size="large" primaryColor="#D02327" />
                  </span>
                  <p className="mt-4 font-bold text-foreground">پیام شما ارسال شد</p>
                  <p className="mt-1.5 text-sm text-muted-foreground">
                    کد پیگیری:{" "}
                    <span className="font-bold text-primary tnum" dir="ltr">
                      {submit.data?.ticket}
                    </span>
                  </p>
                  <div className="mt-5 flex flex-wrap justify-center gap-2">
                    <Button
                      variant="soft"
                      size="sm"
                      onClick={() => {
                        const t = submit.data?.ticket;
                        if (t) void navigator.clipboard?.writeText(t);
                      }}
                    >
                      کپی کد
                    </Button>
                    <Button variant="soft" size="sm" onClick={() => submit.reset()}>
                      ارسال پیام جدید
                    </Button>
                  </div>
                </div>
              </div>
            ) : (
              <form id="contact-form" onSubmit={onSubmit} className="space-y-4">
                {submit.isError && (
                  <p className="rounded-xl bg-destructive/10 px-3.5 py-2.5 text-sm text-destructive">
                    ارسال پیام ناموفق بود. دوباره تلاش کنید.
                  </p>
                )}
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="نام و نام خانوادگی" error={errors.full_name?.message}>
                    <input
                      {...form.register("full_name")}
                      className={fieldInputClass}
                      autoComplete="name"
                    />
                  </Field>
                  <Field label="شماره موبایل" error={errors.phone?.message}>
                    <input
                      {...form.register("phone")}
                      inputMode="tel"
                      autoComplete="tel"
                      className={cn(fieldInputClass, "tnum")}
                      placeholder="۰۹XXXXXXXXX"
                    />
                  </Field>
                </div>
                <Field label="موضوع" error={errors.subject?.message}>
                  <input
                    {...form.register("subject")}
                    className={fieldInputClass}
                    placeholder="مثلاً: پیگیری سفارش، سوال فنی…"
                  />
                </Field>
                <Field label="پیام شما" error={errors.message?.message}>
                  <textarea
                    {...form.register("message")}
                    rows={5}
                    placeholder="شرح مشکل یا درخواست خود را بنویسید…"
                    className={cn(fieldTextareaClass, "min-h-[8.5rem] resize-y")}
                  />
                </Field>
                <Button
                  type="submit"
                  size="lg"
                  className="mt-1 w-full gap-2"
                  disabled={submit.isPending}
                >
                  <Send set="bold" />
                  {submit.isPending ? "در حال ارسال…" : "ارسال پیام"}
                </Button>
              </form>
            )}
          </motion.div>
        </div>
      </Container>
    </div>
  );
}
