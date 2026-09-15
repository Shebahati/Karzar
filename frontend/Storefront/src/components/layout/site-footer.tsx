"use client";

import Link from "next/link";
import { Call, Location, Message, ShieldDone } from "react-iconly";
import { FooterCredentials } from "@/components/layout/footer-credentials";
import { Logo } from "@/components/layout/logo";
import { StoreSocialLinks } from "@/components/social/store-social-links";
import { Container } from "@/components/ui/container";
import {
  STORE_ADDRESS_FA,
  STORE_EMAIL,
  STORE_LANDLINE_DISPLAY,
  STORE_LANDLINE_E164,
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
      { label: "سوالات متداول", href: "/faq" },
    ],
  },
];

export function SiteFooter() {
  return (
    <footer className="relative mt-16 overflow-x-clip bg-[#141615] text-white">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_100%_0%,rgba(208,35,39,0.22),transparent_50%),radial-gradient(ellipse_60%_50%_at_0%_100%,rgba(94,95,94,0.2),transparent_45%)]"
      />

      <Container className="relative pt-14 sm:pt-16">
        <div className="grid gap-10 lg:grid-cols-12 lg:gap-8">
          <div className="order-1 lg:col-span-5">
            <Logo variant="slogan" height={43} tone="onDark" />
            <p className="mt-5 max-w-md text-sm leading-7 text-white/60">
              مرجع تخصصی ابزارآلات صنعتی و تراشکاری.
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
            <div className="mt-7">
              <p
                id="footer-social-heading"
                className="text-xs font-bold tracking-tight text-white/45"
              >
                شبکه‌های اجتماعی
              </p>
              <StoreSocialLinks
                tone="dark"
                variant="icons"
                labelledBy="footer-social-heading"
                className="mt-3"
              />
            </div>
          </div>

          {/* Mobile: after ارتباط, two columns. Desktop: brand → links → contact */}
          <div className="order-3 grid grid-cols-2 gap-6 sm:gap-8 lg:order-2 lg:col-span-4 lg:gap-8">
            {COLUMNS.map((col) => (
              <div key={col.title}>
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
          </div>

          <div className="order-2 lg:order-3 lg:col-span-3">
            <h3 className="text-sm font-black tracking-tight text-white">ارتباط</h3>
            <ul className="mt-4 space-y-3.5 text-sm text-white/60">
              <li>
                <a
                  href={`tel:${STORE_LANDLINE_E164}`}
                  className="flex items-center gap-2.5 transition-colors hover:text-white"
                >
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-primary/20 text-primary">
                    <Call size="small" set="bold" />
                  </span>
                  <span>
                    <span className="block text-xs text-white/45">تلفن ثابت</span>
                    <span dir="ltr" className="min-w-0 tabular-nums tracking-wide">
                      {STORE_LANDLINE_DISPLAY}
                    </span>
                  </span>
                </a>
              </li>
              <li>
                <a
                  href={`tel:${STORE_PHONE_E164}`}
                  className="flex items-center gap-2.5 transition-colors hover:text-white"
                >
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-primary/20 text-primary">
                    <Call size="small" set="bold" />
                  </span>
                  <span>
                    <span className="block text-xs text-white/45">موبایل</span>
                    <span dir="ltr" className="min-w-0 tabular-nums tracking-wide">
                      {STORE_PHONE_DISPLAY}
                    </span>
                  </span>
                </a>
              </li>
              <li>
                <a
                  href={`mailto:${STORE_EMAIL}`}
                  className="flex items-center gap-2.5 transition-colors hover:text-white"
                >
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-white/8">
                    <Message size="small" set="light" />
                  </span>
                  <span dir="ltr" className="min-w-0 break-all">
                    {STORE_EMAIL}
                  </span>
                </a>
              </li>
              <li>
                <a
                  href={STORE_MAPS_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-start gap-2.5 transition-colors hover:text-white"
                >
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-white/8">
                    <Location size="small" set="light" />
                  </span>
                  <span className="min-w-0 flex-1 leading-6 text-pretty">
                    {STORE_ADDRESS_FA}
                  </span>
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-8 min-w-0 sm:mt-10">
          <FooterCredentials />
        </div>

        <div className="mt-6 border-t border-white/10 pt-4 pb-5 text-center text-xs text-white/40 sm:mt-8 sm:pt-5 sm:pb-6 sm:text-start">
          <p className="font-bold text-white/55">
            © 1405 کارزار · تمامی حقوق محفوظ است
          </p>
        </div>
      </Container>
    </footer>
  );
}
