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

/** Square brand mark (white + red K). Do not regenerate a letter-«ک» PNG favicon. */
const BRAND_ICON = {
  url: "/icon.svg",
  type: "image/svg+xml" as const,
  width: 289,
  height: 289,
  alt: "کارزار",
};

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "کارزار | فروشگاه ابزار صنعتی",
    template: "%s | کارزار",
  },
  description:
    "خرید آنلاین ابزارآلات صنعتی و تراشکاری از معتبرترین برندهای جهان با ضمانت اصالت کالا.",
  icons: {
    icon: [{ url: BRAND_ICON.url, type: BRAND_ICON.type }],
    apple: [{ url: BRAND_ICON.url }],
  },
  openGraph: {
    type: "website",
    locale: "fa_IR",
    url: SITE_URL,
    siteName: "کارزار",
    title: "کارزار | فروشگاه ابزار صنعتی",
    description:
      "خرید آنلاین ابزارآلات صنعتی و تراشکاری از معتبرترین برندهای جهان با ضمانت اصالت کالا.",
    images: [
      {
        url: BRAND_ICON.url,
        width: BRAND_ICON.width,
        height: BRAND_ICON.height,
        alt: BRAND_ICON.alt,
      },
    ],
  },
  twitter: {
    card: "summary",
    title: "کارزار | فروشگاه ابزار صنعتی",
    description:
      "خرید آنلاین ابزارآلات صنعتی و تراشکاری از معتبرترین برندهای جهان با ضمانت اصالت کالا.",
    images: [BRAND_ICON.url],
  },
  // Do not set alternates.canonical here. Next.js inherits root canonicals onto
  // every descendant that does not override them (GSC: /contact, /about, /terms
  // were observed with homepage as user-declared canonical).
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
      className={cn(
        "h-full w-full max-w-full overflow-x-clip overscroll-x-none",
        iranYekan.variable,
      )}
    >
      <head>
        {/* First-visit splash FOUC gate — sessionStorage; must run before paint (CSP nonce).
            Injects a <style data-karzar-splash-boot> ONLY. Must NEVER set attrs on <html>
            (React owns that node — pre-hydrate documentElement.setAttribute caused hydration
            mismatch). Strips leftover data-karzar-splash from older builds. FirstVisitSplash
            removes the boot style on dismiss; boot also self-dismisses (load+1s / 2.8s max).
            suppressHydrationWarning: browsers clear script[nonce] from the DOM IDL after
            parse (getAttribute → ""), so React would otherwise warn prop≠DOM. */}
        <script
          nonce={nonce}
          suppressHydrationWarning
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var h=document.documentElement;h.removeAttribute("data-karzar-splash");var k="karzar-splash-seen";if(sessionStorage.getItem(k))return;var s=document.createElement("style");s.setAttribute("data-karzar-splash-boot","");s.textContent='html{overflow:hidden!important}body::before{content:"";position:fixed;inset:0;z-index:10000;pointer-events:auto;background:radial-gradient(ellipse 90% 70% at 50% 42%,#fff 0%,transparent 58%),linear-gradient(165deg,#f7f6f4 0%,#eef0f1 45%,#e6e8ea 100%)}';(document.head||h).appendChild(s);var done=0;function dismiss(){if(done)return;done=1;h.removeAttribute("data-karzar-splash");if(s.parentNode)s.parentNode.removeChild(s)}window.addEventListener("load",function(){setTimeout(dismiss,1000)},{once:true});setTimeout(dismiss,2800)}catch(e){}})();`,
          }}
        />
        {/* Analytics: set NEXT_PUBLIC_GA_MEASUREMENT_ID *or* NEXT_PUBLIC_GTM_ID — not both. */}
        <GoogleTagManagerHead nonce={nonce} />
        <GoogleAnalytics nonce={nonce} />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(sitewideJsonLd) }}
        />
      </head>
      <body className="font-sans min-h-full w-full max-w-full overflow-x-clip overscroll-x-none bg-background text-foreground antialiased">
        <GoogleTagManagerNoscript />
        <a href="#main-content" className="skip-link">
          پرش به محتوای اصلی
        </a>
        <Providers>
          {/* React-owned splash; head boot <style> bridges FOUC until overlay paints. */}
          <FirstVisitSplash />
          <SiteHeader />
          {/* Clearance for fixed mobile bottom nav (~4.5rem + iOS home indicator). */}
          <div className="w-full max-w-full min-w-0 overflow-x-clip overscroll-x-none pb-[calc(4.75rem+env(safe-area-inset-bottom,0px))] lg:pb-0">
            <main
              id="main-content"
              tabIndex={-1}
              className="min-h-[60svh] w-full max-w-full min-w-0 overflow-x-clip overscroll-x-none outline-none"
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
