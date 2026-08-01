import type { Metadata, Viewport } from "next";
import { headers } from "next/headers";
import "./globals.css";
import { Providers } from "./providers";
import { SiteHeader } from "@/components/layout/site-header";
import { SiteFooter } from "@/components/layout/site-footer";
import { MobileBottomNav } from "@/components/layout/mobile-bottom-nav";
import {
  GoogleTagManagerHead,
  GoogleTagManagerNoscript,
} from "@/components/analytics/google-tag-manager";
import { GoogleAnalytics } from "@/components/analytics/google-analytics";
import { iranYekan } from "@/lib/fonts";
import { buildSitewideJsonLd } from "@/lib/json-ld";
import { NOINDEX_NOFOLLOW } from "@/lib/crawl-hygiene";
import { getSiteUrl, isSeoIndexable } from "@/lib/site-url";
import { cn } from "@/lib/utils";

const SITE_URL = getSiteUrl();
const sitewideJsonLd = buildSitewideJsonLd();

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "کارزار | فروشگاه ابزار صنعتی",
    template: "%s | کارزار",
  },
  description:
    "خرید آنلاین ابزارآلات صنعتی و تراشکاری از معتبرترین برندهای جهان با ضمانت اصالت کالا.",
  openGraph: {
    type: "website",
    locale: "fa_IR",
    url: SITE_URL,
    siteName: "کارزار",
    title: "کارزار | فروشگاه ابزار صنعتی",
    description:
      "خرید آنلاین ابزارآلات صنعتی و تراشکاری از معتبرترین برندهای جهان با ضمانت اصالت کالا.",
  },
  twitter: {
    card: "summary_large_image",
    title: "کارزار | فروشگاه ابزار صنعتی",
    description:
      "خرید آنلاین ابزارآلات صنعتی و تراشکاری از معتبرترین برندهای جهان با ضمانت اصالت کالا.",
  },
  alternates: {
    canonical: SITE_URL,
  },
  ...(isSeoIndexable() ? {} : { robots: NOINDEX_NOFOLLOW }),
};

export const viewport: Viewport = {
  themeColor: "#D02327",
  viewportFit: "cover",
};

export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const nonce = (await headers()).get("x-nonce") ?? undefined;

  return (
    <html
      lang="fa"
      dir="rtl"
      data-scroll-behavior="smooth"
      className={cn("h-full", iranYekan.variable)}
    >
      <head>
        {/* Analytics: set NEXT_PUBLIC_GA_MEASUREMENT_ID *or* NEXT_PUBLIC_GTM_ID — not both. */}
        <GoogleTagManagerHead nonce={nonce} />
        <GoogleAnalytics nonce={nonce} />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(sitewideJsonLd) }}
        />
      </head>
      <body className="font-sans min-h-full bg-background text-foreground antialiased">
        <GoogleTagManagerNoscript />
        <a href="#main-content" className="skip-link">
          پرش به محتوای اصلی
        </a>
        <Providers>
          <SiteHeader />
          {/* Clearance for fixed mobile bottom nav (~4.5rem + iOS home indicator). */}
          <div className="pb-[calc(4.75rem+env(safe-area-inset-bottom,0px))] lg:pb-0">
            <main id="main-content" tabIndex={-1} className="min-h-[60vh] outline-none">
              {children}
            </main>
            <SiteFooter />
          </div>
          <MobileBottomNav />
        </Providers>
      </body>
    </html>
  );
}
