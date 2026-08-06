import type { Metadata, Viewport } from "next";
import { headers } from "next/headers";
import "./globals.css";
import { Providers } from "./providers";
import { SiteHeader } from "@/components/layout/site-header";
import { SiteFooter } from "@/components/layout/site-footer";
import { MobileBottomNav } from "@/components/layout/mobile-bottom-nav";
import { FirstVisitSplash } from "@/components/layout/first-visit-splash";
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
      className={cn("h-full w-full max-w-full overflow-x-clip", iranYekan.variable)}
    >
      <head>
        {/* First-visit splash gate — sessionStorage; must run before paint (CSP nonce). */}
        <script
          nonce={nonce}
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var k="karzar-splash-seen";if(sessionStorage.getItem(k))return;var h=document.documentElement;h.setAttribute("data-karzar-splash","");var done=0;function dismiss(){if(done)return;done=1;try{sessionStorage.setItem(k,"1")}catch(e){}h.removeAttribute("data-karzar-splash")}window.addEventListener("load",function(){setTimeout(dismiss,1000)},{once:true});setTimeout(dismiss,2800)}catch(e){}})();`,
          }}
        />
        {/* Analytics: set NEXT_PUBLIC_GA_MEASUREMENT_ID *or* NEXT_PUBLIC_GTM_ID — not both. */}
        <GoogleTagManagerHead nonce={nonce} />
        <GoogleAnalytics nonce={nonce} />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(sitewideJsonLd) }}
        />
        <noscript>
          <style
            dangerouslySetInnerHTML={{
              __html:
                "html[data-karzar-splash]{overflow:auto!important}html[data-karzar-splash] body::before{content:none!important;display:none!important}",
            }}
          />
        </noscript>
      </head>
      <body className="font-sans min-h-full w-full max-w-full overflow-x-clip bg-background text-foreground antialiased">
        <GoogleTagManagerNoscript />
        <a href="#main-content" className="skip-link">
          پرش به محتوای اصلی
        </a>
        <Providers>
          {/* React-owned splash; CSS body::before bridges FOUC until mount. */}
          <FirstVisitSplash />
          <SiteHeader />
          {/* Clearance for fixed mobile bottom nav (~4.5rem + iOS home indicator). */}
          <div className="w-full max-w-full overflow-x-clip pb-[calc(4.75rem+env(safe-area-inset-bottom,0px))] lg:pb-0">
            <main
              id="main-content"
              tabIndex={-1}
              className="min-h-[60vh] w-full max-w-full overflow-x-clip outline-none"
            >
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
