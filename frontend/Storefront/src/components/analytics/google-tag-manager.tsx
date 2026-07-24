import Script from "next/script";

/**
 * GTM container ID from build-time env. Empty disables GTM.
 * Prefer either GTM *or* first-party GA4 (`NEXT_PUBLIC_GA_MEASUREMENT_ID`), not both
 * for the same property — otherwise page views double-count.
 */
export const GTM_ID = process.env.NEXT_PUBLIC_GTM_ID?.trim() ?? "";

/**
 * GTM head snippet — load as early as possible (beforeInteractive → document head).
 */
export function GoogleTagManagerHead({ nonce }: { nonce?: string }) {
  if (!GTM_ID) return null;

  return (
    <Script id="google-tag-manager" strategy="beforeInteractive" nonce={nonce}>{`
(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
})(window,document,'script','dataLayer','${GTM_ID}');
`.trim()}</Script>
  );
}

/**
 * GTM noscript fallback — must be the first child inside <body>.
 */
export function GoogleTagManagerNoscript() {
  if (!GTM_ID) return null;

  return (
    <noscript>
      <iframe
        src={`https://www.googletagmanager.com/ns.html?id=${GTM_ID}`}
        height="0"
        width="0"
        style={{ display: "none", visibility: "hidden" }}
        title="Google Tag Manager"
      />
    </noscript>
  );
}
