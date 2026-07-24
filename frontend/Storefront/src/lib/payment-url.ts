/** Allowlist for gateway redirects before assigning window.location. */

const ALLOWED_PAYMENT_HOSTS = new Set([
  "www.zarinpal.com",
  "zarinpal.com",
  "sandbox.zarinpal.com",
  "payment.zarinpal.com",
]);

function isLocalDevHost(hostname: string): boolean {
  return hostname === "localhost" || hostname === "127.0.0.1";
}

/**
 * Returns true when `url` is a safe absolute http(s) payment redirect target.
 * Localhost http is allowed only for mock / local callback flows.
 */
export function isAllowedPaymentUrl(url: string): boolean {
  if (!url || typeof url !== "string") return false;
  let parsed: URL;
  try {
    parsed = new URL(url.trim());
  } catch {
    return false;
  }
  if (parsed.protocol !== "https:" && parsed.protocol !== "http:") return false;
  const host = parsed.hostname.toLowerCase();
  if (ALLOWED_PAYMENT_HOSTS.has(host)) {
    return parsed.protocol === "https:" || isLocalDevHost(host);
  }
  if (isLocalDevHost(host)) {
    return true;
  }
  // Same-origin relative storefront callback (mock provider may return absolute same host).
  if (typeof window !== "undefined" && host === window.location.hostname) {
    return true;
  }
  return false;
}

/** Navigate only when the URL passes the payment host allowlist. */
export function redirectToPaymentUrl(url: string): void {
  if (!isAllowedPaymentUrl(url)) {
    throw new Error("PAYMENT_URL_NOT_ALLOWED");
  }
  window.location.href = url;
}
