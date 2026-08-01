"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { motion } from "framer-motion";
import { Call, Location, Message, Send, TickSquare } from "react-iconly";
import { Container } from "@/components/ui/container";
import { Button } from "@/components/ui/button";
import { Field, fieldInputClass, fieldTextareaClass } from "@/components/ui/field";
import { NeshanDirectionsButton } from "@/components/contact/neshan-directions-button";
import { NeshanMapEmbed } from "@/components/contact/neshan-map-embed";
import { contactSchema, type ContactValues } from "@/lib/validation";
import { useSubmitContact } from "@/features/checkout/queries";
import {
  STORE_ADDRESS_FA,
  STORE_EMAIL,
  STORE_MAPS_URL,
  STORE_PHONE_DISPLAY,
  STORE_PHONE_E164,
} from "@/lib/store-location";

const DETAILS = [
  {
    Icon: Message,
    label: "ایمیل پشتیبانی",
    value: STORE_EMAIL,
    href: `mailto:${STORE_EMAIL}`,
  },
  {
    Icon: Call,
    label: "تماس تلفنی",
    value: STORE_PHONE_DISPLAY,
    href: `tel:${STORE_PHONE_E164}`,
  },
  {
    Icon: Location,
    label: "نشانی",
    value: STORE_ADDRESS_FA,
    href: STORE_MAPS_URL,
    external: true,
  },
];

export function ContactView() {
  const form = useForm<ContactValues>({ resolver: zodResolver(contactSchema) });
  const submit = useSubmitContact();
  const { errors } = form.formState;

  const onSubmit = form.handleSubmit((values) =>
    submit.mutate(values, { onSuccess: () => form.reset() }),
  );

  return (
    <div className="bg-hero-glow">
      <Container className="py-10 lg:py-16">
        <div className="mb-10 text-center">
          <span className="inline-block rounded-full bg-accent px-3 py-1 text-xs font-bold text-primary">
            ارتباط با ما
          </span>
          <h1 className="mt-4 text-3xl font-bold text-foreground">
            با کارشناسان کارزار در تماس باشید
          </h1>
          <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
            سوال، مشاوره یا همکاری؟ پیام خود را بفرستید؛ سریع پاسخ می‌دهیم.
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Form */}
          <motion.div
            initial={{ opacity: 0, x: 24 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.45 }}
            className="glass-strong rounded-3xl p-6 shadow-elevated sm:p-8"
          >
            {submit.isSuccess ? (
              <div className="grid h-full place-items-center py-10 text-center">
                <span className="grid h-16 w-16 place-items-center rounded-full bg-success text-success-foreground shadow-elevated">
                  <TickSquare set="bold" size="large" />
                </span>
                <p className="mt-4 font-bold text-foreground">پیام شما ارسال شد</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  کد پیگیری: <span className="font-bold tnum" dir="ltr">{submit.data?.ticket}</span>
                </p>
                <div className="mt-4 flex flex-wrap justify-center gap-2">
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
                  <Button variant="soft" className="mt-0" onClick={() => submit.reset()}>
                    ارسال پیام جدید
                  </Button>
                </div>
              </div>
            ) : (
              <form id="contact-form" onSubmit={onSubmit} className="space-y-4">
                {submit.isError && (
                  <p className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
                    ارسال پیام ناموفق بود. دوباره تلاش کنید.
                  </p>
                )}
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="نام و نام خانوادگی" error={errors.full_name?.message}>
                    <input {...form.register("full_name")} className={fieldInputClass} />
                  </Field>
                  <Field label="شماره موبایل" error={errors.phone?.message}>
                    <input
                      {...form.register("phone")}
                      inputMode="tel"
                      className={`${fieldInputClass} tnum`}
                      placeholder="۰۹XXXXXXXXX"
                    />
                  </Field>
                </div>
                <Field label="موضوع" error={errors.subject?.message}>
                  <input {...form.register("subject")} className={fieldInputClass} />
                </Field>
                <Field label="پیام شما" error={errors.message?.message}>
                  <textarea
                    {...form.register("message")}
                    rows={5}
                    className={fieldTextareaClass}
                  />
                </Field>
                <Button type="submit" size="lg" className="w-full gap-2" disabled={submit.isPending}>
                  <Send set="bold" />
                  {submit.isPending ? "در حال ارسال…" : "ارسال پیام"}
                </Button>
              </form>
            )}
          </motion.div>

          {/* Details */}
          <motion.div
            initial={{ opacity: 0, x: -24 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.45 }}
            className="space-y-4"
          >
            <div id="store-address" className="grid gap-3 scroll-mt-24">
              {DETAILS.map(({ Icon, label, value, href, external }) => (
                <a
                  key={label}
                  href={href}
                  {...(external
                    ? { target: "_blank", rel: "noopener noreferrer" }
                    : {})}
                  className="flex items-center gap-4 rounded-2xl bg-card p-5 shadow-soft transition-shadow hover:shadow-card"
                >
                  <span className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-accent text-primary">
                    <Icon set="bold" />
                  </span>
                  <div>
                    <p className="text-xs text-muted-foreground">{label}</p>
                    <p className="mt-0.5 font-bold text-foreground" dir={label === "تماس تلفنی" ? "ltr" : undefined}>
                      {value}
                    </p>
                  </div>
                </a>
              ))}
            </div>

            <NeshanDirectionsButton className="w-full" size="lg" />
          </motion.div>
        </div>

        {/* Full-width Neshan map */}
        <motion.section
          aria-labelledby="store-map-heading"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.45 }}
          className="mt-8 space-y-4 sm:mt-10"
        >
          <div className="flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center">
            <div>
              <h2 id="store-map-heading" className="text-lg font-bold text-foreground">
                موقعیت فروشگاه روی نقشه نشان
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                پاساژ فجر، پلاک ۱۰۸ — مسیر را با نشان باز کنید.
              </p>
            </div>
            <NeshanDirectionsButton className="shrink-0" />
          </div>
          <NeshanMapEmbed className="w-full" />
        </motion.section>
      </Container>
    </div>
  );
}
