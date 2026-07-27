"use client";

import Link from "next/link";
import { Call, Location, Message, ShieldDone } from "react-iconly";
import { Logo } from "@/components/layout/logo";
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
    title: "خدمات مشتریان",
    links: [
      { label: "تماس با ما", href: "/contact" },
      { label: "قوانین استفاده", href: "/terms" },
      { label: "حریم خصوصی", href: "/privacy" },
      { label: "استعلام قیمت", href: "/quote" },
      { label: "سبد خرید", href: "/cart" },
    ],
  },
];

const TRUST = [
  { icon: ShieldDone, label: "ضمانت اصالت کالا" },
  { icon: Call, label: "پشتیبانی تخصصی" },
  { icon: Message, label: "مشاوره خرید" },
];

export function SiteFooter() {
  return (
    <footer className="mt-20 bg-white pt-14 shadow-[0_-1px_0_rgba(16,24,40,0.04)]">
      <Container>
        <div className="grid gap-10 lg:grid-cols-12">
          <div className="lg:col-span-4">
            <Logo variant="slogan" height={48} />
            <p className="mt-4 max-w-sm text-sm leading-7 text-steel">
              کارزار، مرجع تخصصی خرید ابزارآلات صنعتی و تراشکاری از معتبرترین
              برندهای جهان با ضمانت اصالت و پشتیبانی حرفه‌ای.
            </p>
            <div className="mt-6 flex flex-wrap gap-2">
              {TRUST.map(({ icon: Icon, label }) => (
                <span
                  key={label}
                  className="inline-flex items-center gap-1.5 rounded-full bg-secondary px-3 py-1.5 text-xs font-bold text-steel"
                >
                  <Icon size="small" set="bold" primaryColor="#5E5F5E" />
                  {label}
                </span>
              ))}
            </div>
          </div>

          {COLUMNS.map((col) => (
            <div key={col.title} className="lg:col-span-2">
              <h3 className="text-sm font-bold text-foreground">{col.title}</h3>
              <ul className="mt-4 space-y-2.5">
                {col.links.map((link) => (
                  <li key={link.label}>
                    <Link
                      href={link.href}
                      className="text-sm text-muted-foreground transition-colors hover:text-primary"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}

          <div className="lg:col-span-4">
            <h3 className="text-sm font-bold text-foreground">ارتباط با ما</h3>
            <ul className="mt-4 space-y-3 text-sm text-muted-foreground">
              <li className="flex items-center gap-2.5">
                <Call size="small" set="light" />
                <a
                  href={`tel:${STORE_PHONE_E164}`}
                  className="transition-colors hover:text-primary tnum"
                  dir="ltr"
                >
                  {STORE_PHONE_DISPLAY}
                </a>
              </li>
              <li className="flex items-center gap-2.5">
                <Message size="small" set="light" />
                <a
                  href={`mailto:${STORE_EMAIL}`}
                  className="transition-colors hover:text-primary"
                  dir="ltr"
                >
                  {STORE_EMAIL}
                </a>
              </li>
              <li className="flex items-start gap-2.5">
                <Location size="small" set="light" />
                <a
                  href={STORE_MAPS_URL}
                  className="transition-colors hover:text-primary"
                >
                  {STORE_ADDRESS_FA}
                </a>
              </li>
              <li className="flex items-start gap-2.5 pt-1">
                <span
                  className="inline-flex min-h-[48px] min-w-[48px] items-center justify-center rounded-lg border border-border/70 bg-secondary px-3 text-[10px] font-bold text-muted-foreground"
                  title="نماد اعتماد الکترونیکی"
                >
                  نماد اعتماد
                </span>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-12 flex flex-col items-center justify-between gap-3 border-t border-border/60 pt-6 text-xs text-muted-foreground sm:flex-row">
          <p>© {new Date().getFullYear()} فروشگاه کارزار. تمامی حقوق محفوظ است.</p>
          <p>تأمین تخصصی ابزار برای صنعتگران ایران</p>
        </div>
      </Container>
    </footer>
  );
}
