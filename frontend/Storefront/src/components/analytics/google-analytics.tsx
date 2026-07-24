import Script from "next/script";

/**
 * GA4 Measurement ID from build-time env.
 * Prefer setting `NEXT_PUBLIC_GA_MEASUREMENT_ID` at deploy (requires rebuild).
 *
 * When GTM is also enabled (`NEXT_PUBLIC_GTM_ID`), this component stays off to
 * avoid double-counting — configure GA4 inside the GTM container instead.
 */
export const GA_MEASUREMENT_ID =
  process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID?.trim() ?? "";

const GTM_ID = process.env.NEXT_PUBLIC_GTM_ID?.trim() ?? "";

export function GoogleAnalytics({ nonce }: { nonce?: string }) {
  if (!GA_MEASUREMENT_ID || GTM_ID) return null;

  return (
    <>
      <Script
        src={`https://www.googletagmanager.com/gtag/js?id=${GA_MEASUREMENT_ID}`}
        strategy="afterInteractive"
        nonce={nonce}
      />
      <Script id="google-analytics-gtag" strategy="afterInteractive" nonce={nonce}>{`
window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('js', new Date());
gtag('config', '${GA_MEASUREMENT_ID}');
`.trim()}</Script>
    </>
  );
}
