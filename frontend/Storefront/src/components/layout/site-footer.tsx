"use client";

import Link from "next/link";
import { Call, Location, Message, ShieldDone } from "react-iconly";
import { Logo } from "@/components/layout/logo";
import { NeshanDirectionsButton } from "@/components/contact/neshan-directions-button";
import { Container } from "@/components/ui/container";
import {
  STORE_ADDRESS_FA,
  STORE_EMAIL,
  STORE_MAPS_URL,
  STORE_PHONE_DISPLAY,
  STORE_PHONE_E164,
} from "@/lib/store-location";

const COLUMNS = [
  {
    title: "دسترسی سریع",
    links: [
      { label: "فروشگاه", href: "/catalog" },
      { label: "مجله کارزار", href: "/blog" },
      { label: "درباره ما", href: "/about" },
      { label: "ورود / ثبت‌نام", href: "/login" },
    ],
  },
  {
    title: "خدمات",
    links: [
      { label: "تماس با ما", href: "/contact" },
      { label: "استعلام قیمت", href: "/quote" },
      { label: "سبد خرید", href: "/cart" },
      { label: "قوانین", href: "/terms" },
      { label: "حریم خصوصی", href: "/privacy" },
    ],
  },
];

export function SiteFooter() {
  return (
    <footer className="relative mt-16 overflow-hidden bg-[#141615] text-white">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_100%_0%,rgba(208,35,39,0.22),transparent_50%),radial-gradient(ellipse_60%_50%_at_0%_100%,rgba(94,95,94,0.2),transparent_45%)]"
      />

      <Container className="relative pt-14 sm:pt-16">
        <div className="grid gap-10 lg:grid-cols-12 lg:gap-8">
          <div className="lg:col-span-5">
            <Logo variant="slogan" height={43} tone="onDark" />
            <p className="mt-5 max-w-md text-sm leading-7 text-white/60">
              مرجع تخصصی ابزارآلات صنعتی و تراشکاری — اصالت، تأمین سریع و پشتیبانی کارگاهی.
            </p>
            <div className="mt-6 flex flex-wrap gap-2">
              {["ضمانت اصالت", "ارسال سراسری", "مشاوره تخصصی"].map((label) => (
                <span
                  key={label}
                  className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-bold text-white/80"
                >
                  <ShieldDone size="small" set="bold" primaryColor="#D02327" />
                  {label}
                </span>
              ))}
            </div>
          </div>

          {COLUMNS.map((col) => (
            <div key={col.title} className="lg:col-span-2">
              <h3 className="text-sm font-black tracking-tight text-white">{col.title}</h3>
              <ul className="mt-4 space-y-2.5">
                {col.links.map((link) => (
                  <li key={link.label}>
                    <Link
                      href={link.href}
                      className="text-sm text-white/55 transition-colors hover:text-primary"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}

          <div className="lg:col-span-3">
            <h3 className="text-sm font-black tracking-tight text-white">ارتباط</h3>
            <ul className="mt-4 space-y-3 text-sm text-white/60">
              <li>
                <a
                  href={`tel:${STORE_PHONE_E164}`}
                  className="inline-flex items-center gap-2.5 transition-colors hover:text-white"
                  dir="ltr"
                >
                  <span className="grid h-9 w-9 place-items-center rounded-full bg-primary/20 text-primary">
                    <Call size="small" set="bold" />
                  </span>
                  {STORE_PHONE_DISPLAY}
                </a>
              </li>
              <li>
                <a
                  href={`mailto:${STORE_EMAIL}`}
                  className="inline-flex items-center gap-2.5 transition-colors hover:text-white"
                  dir="ltr"
                >
                  <span className="grid h-9 w-9 place-items-center rounded-full bg-white/8">
                    <Message size="small" set="light" />
                  </span>
                  {STORE_EMAIL}
                </a>
              </li>
              <li>
                <a
                  href={STORE_MAPS_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-start gap-2.5 transition-colors hover:text-white"
                >
                  <span className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-full bg-white/8">
                    <Location size="small" set="light" />
                  </span>
                  <span className="leading-6">{STORE_ADDRESS_FA}</span>
                </a>
              </li>
            </ul>
            <NeshanDirectionsButton tone="dark" className="mt-5 w-full sm:w-auto" />
          </div>
        </div>

        <div className="mt-12 flex flex-col items-center justify-between gap-3 border-t border-white/10 py-6 text-xs text-white/40 sm:flex-row">
          <p>© {new Date().getFullYear()} کارزار · تمامی حقوق محفوظ است</p>
          <p className="font-bold text-white/55">تأمین تخصصی ابزار برای صنعتگران ایران</p>
        </div>
      </Container>
    </footer>
  );
}
