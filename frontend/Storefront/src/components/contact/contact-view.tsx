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
import { StoreSocialLinks } from "@/components/social/store-social-links";
import { contactSchema, type ContactValues } from "@/lib/validation";
import { useSubmitContact } from "@/features/checkout/queries";
import {
  STORE_ADDRESS_FA,
  STORE_EMAIL,
  STORE_MAPS_URL,
  STORE_PHONE_DISPLAY,
  STORE_PHONE_E164,
} from "@/lib/store-location";
import { cn } from "@/lib/utils";

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
    <div className="w-full max-w-full overflow-x-clip bg-hero-glow">
      <Container
        className={cn(
          "py-[clamp(1.25rem,3.5svh,4rem)]",
          "lg:py-[clamp(1.25rem,4svh,4rem)]",
          "[@media(max-height:760px)]:py-4",
          "[@media(max-height:640px)]:py-3",
        )}
      >
        <div
          className={cn(
            "mb-[clamp(1rem,2.8svh,2.5rem)] text-center",
            "[@media(max-height:760px)]:mb-4",
            "[@media(max-height:640px)]:mb-3",
          )}
        >
          <span
            className={cn(
              "inline-block rounded-full bg-accent px-3 py-1 text-xs font-bold text-primary",
              "[@media(max-height:640px)]:py-0.5",
            )}
          >
            ارتباط با ما
          </span>
          <h1
            className={cn(
              "mt-[clamp(0.5rem,1.4svh,1rem)] font-bold text-foreground",
              "text-[clamp(1.35rem,1.1rem+1.6svh,1.875rem)]",
              "[@media(max-height:640px)]:mt-1.5",
            )}
          >
            با کارشناسان کارزار در تماس باشید
          </h1>
          <p
            className={cn(
              "mx-auto mt-[clamp(0.25rem,0.9svh,0.5rem)] max-w-md text-sm text-muted-foreground",
              "[@media(max-height:720px)]:mt-1 [@media(max-height:720px)]:text-xs",
              "[@media(max-height:640px)]:line-clamp-2",
            )}
          >
            سوال، مشاوره یا همکاری؟ پیام خود را بفرستید؛ سریع پاسخ می‌دهیم.
          </p>
        </div>

        <div
          className={cn(
            "grid min-w-0 gap-[clamp(0.75rem,2svh,1.5rem)] lg:grid-cols-2 lg:items-start",
            "[@media(max-height:760px)]:gap-4",
            "[@media(max-height:640px)]:gap-3",
          )}
        >
          {/* Form */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.45 }}
            className={cn(
              "min-w-0 overflow-hidden glass-strong rounded-3xl shadow-elevated",
              "p-[clamp(1rem,2.4svh,2rem)] sm:p-[clamp(1.25rem,2.8svh,2rem)]",
              "[@media(max-height:760px)]:rounded-2xl [@media(max-height:760px)]:p-4",
              "[@media(max-height:640px)]:p-3.5",
            )}
          >
            {submit.isSuccess ? (
              <div
                className={cn(
                  "grid h-full place-items-center text-center",
                  "py-[clamp(1.5rem,4svh,2.5rem)]",
                )}
              >
                <span className="grid h-16 w-16 place-items-center rounded-full bg-success text-success-foreground shadow-elevated [@media(max-height:720px)]:h-12 [@media(max-height:720px)]:w-12">
                  <TickSquare set="bold" size="large" />
                </span>
                <p className="mt-4 font-bold text-foreground [@media(max-height:720px)]:mt-2">
                  پیام شما ارسال شد
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  کد پیگیری:{" "}
                  <span className="font-bold tnum" dir="ltr">
                    {submit.data?.ticket}
                  </span>
                </p>
                <div className="mt-4 flex flex-wrap justify-center gap-2 [@media(max-height:720px)]:mt-2">
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
              <form
                id="contact-form"
                onSubmit={onSubmit}
                className={cn(
                  "space-y-[clamp(0.5rem,1.4svh,1rem)]",
                  "[@media(max-height:760px)]:space-y-2.5",
                  "[@media(max-height:640px)]:space-y-2",
                )}
              >
                {submit.isError && (
                  <p className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
                    ارسال پیام ناموفق بود. دوباره تلاش کنید.
                  </p>
                )}
                <div
                  className={cn(
                    "grid gap-[clamp(0.5rem,1.4svh,1rem)] sm:grid-cols-2",
                    "[@media(max-height:760px)]:gap-2.5",
                  )}
                >
                  <Field label="نام و نام خانوادگی" error={errors.full_name?.message}>
                    <input
                      {...form.register("full_name")}
                      className={cn(fieldInputClass, "[@media(max-height:720px)]:min-h-11 [@media(max-height:720px)]:h-11")}
                    />
                  </Field>
                  <Field label="شماره موبایل" error={errors.phone?.message}>
                    <input
                      {...form.register("phone")}
                      inputMode="tel"
                      className={cn(
                        fieldInputClass,
                        "tnum",
                        "[@media(max-height:720px)]:min-h-11 [@media(max-height:720px)]:h-11",
                      )}
                      placeholder="۰۹XXXXXXXXX"
                    />
                  </Field>
                </div>
                <Field label="موضوع" error={errors.subject?.message}>
                  <input
                    {...form.register("subject")}
                    className={cn(fieldInputClass, "[@media(max-height:720px)]:min-h-11 [@media(max-height:720px)]:h-11")}
                    placeholder="مثلاً: پیگیری سفارش، سوال فنی…"
                  />
                </Field>
                <Field label="پیام شما" error={errors.message?.message}>
                  <textarea
                    {...form.register("message")}
                    rows={3}
                    placeholder="شرح مشکل یا درخواست خود را بنویسید…"
                    className={cn(
                      fieldTextareaClass,
                      /* Height from viewport, not rows — avoids cut-off on short laptops */
                      "h-[clamp(4.5rem,12svh,7.5rem)] resize-y",
                      "[@media(max-height:760px)]:h-[4.5rem]",
                      "[@media(max-height:720px)]:py-2.5",
                      "[@media(max-height:640px)]:h-[3.75rem]",
                    )}
                  />
                </Field>
                <Button
                  type="submit"
                  size="lg"
                  className={cn(
                    "w-full gap-2",
                    "[@media(max-height:720px)]:h-10 [@media(max-height:720px)]:text-sm",
                  )}
                  disabled={submit.isPending}
                >
                  <Send set="bold" />
                  {submit.isPending ? "در حال ارسال…" : "ارسال پیام"}
                </Button>
              </form>
            )}
          </motion.div>

          {/* Details */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.45 }}
            className={cn(
              "min-w-0 space-y-[clamp(0.5rem,1.4svh,1rem)]",
              "[@media(max-height:760px)]:space-y-2.5",
              "[@media(max-height:640px)]:space-y-2",
            )}
          >
            <div
              id="store-address"
              className="grid gap-[clamp(0.4rem,1svh,0.75rem)] scroll-mt-24"
            >
              {DETAILS.map(({ Icon, label, value, href, external }) => (
                <a
                  key={label}
                  href={href}
                  {...(external
                    ? { target: "_blank", rel: "noopener noreferrer" }
                    : {})}
                  className={cn(
                    "flex min-w-0 items-center gap-4 overflow-hidden rounded-2xl bg-card shadow-soft transition-shadow hover:shadow-card",
                    "p-[clamp(0.75rem,1.6svh,1.25rem)]",
                    "[@media(max-height:760px)]:gap-3 [@media(max-height:760px)]:rounded-xl [@media(max-height:760px)]:p-3",
                    "[@media(max-height:640px)]:p-2.5",
                  )}
                >
                  <span
                    className={cn(
                      "grid shrink-0 place-items-center rounded-xl bg-accent text-primary",
                      "h-12 w-12",
                      "[@media(max-height:760px)]:h-10 [@media(max-height:760px)]:w-10",
                      "[@media(max-height:640px)]:h-9 [@media(max-height:640px)]:w-9 [@media(max-height:640px)]:rounded-lg",
                    )}
                  >
                    <Icon set="bold" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs text-muted-foreground">{label}</p>
                    <p
                      className={cn(
                        "mt-0.5 break-words font-bold text-foreground",
                        "[@media(max-height:640px)]:text-sm",
                      )}
                      dir={label === "تماس تلفنی" ? "ltr" : undefined}
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
                className={cn(
                  "mb-2 text-xs font-bold text-[#5E5F5E]",
                  "[@media(max-height:760px)]:mb-1.5",
                  "[@media(max-height:640px)]:sr-only",
                )}
              >
                پیام‌رسان‌ها
              </p>
              <StoreSocialLinks
                tone="light"
                variant="pills"
                labelledBy="contact-social-heading"
              />
            </div>

            {/* Compact Neshan location — height tracks viewport */}
            <section
              aria-labelledby="store-map-heading"
              className="overflow-hidden rounded-2xl border border-[#5E5F5E]/12 bg-card [@media(max-height:760px)]:rounded-xl"
            >
              <div
                className={cn(
                  "flex flex-col gap-3 border-b border-[#5E5F5E]/10 sm:flex-row sm:items-center sm:justify-between",
                  "px-4 py-[clamp(0.5rem,1.2svh,0.75rem)]",
                  "[@media(max-height:760px)]:gap-2 [@media(max-height:760px)]:px-3 [@media(max-height:760px)]:py-2",
                )}
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span
                      aria-hidden
                      className="h-1.5 w-1.5 shrink-0 rounded-full bg-primary"
                    />
                    <h2
                      id="store-map-heading"
                      className="text-sm font-bold text-foreground [@media(max-height:640px)]:text-xs"
                    >
                      موقعیت فروشگاه روی نقشه نشان
                    </h2>
                  </div>
                  <p
                    className={cn(
                      "mt-1 text-xs leading-5 text-[#5E5F5E]",
                      "[@media(max-height:720px)]:mt-0.5 [@media(max-height:720px)]:leading-4",
                      "[@media(max-height:640px)]:line-clamp-1",
                    )}
                  >
                    پاساژ فجر، پلاک ۱۰۸ — مسیر را با نشان باز کنید.
                  </p>
                </div>
                <NeshanDirectionsButton size="sm" className="w-full sm:w-auto" />
              </div>
              <NeshanMapEmbed className="rounded-none ring-0" />
            </section>
          </motion.div>
        </div>
      </Container>
    </div>
  );
}
