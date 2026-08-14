import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import {
  catalogProductByIdUrl,
  encodedProductSlugPath,
  numericProductPathId,
} from "@/lib/product-url";

const isDev = process.env.NODE_ENV !== "production";
const PRODUCT_LOOKUP_TIMEOUT_MS = 2000;

function apiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
}

function apiConnectOrigins(): string {
  const origins = new Set<string>(["http://localhost:8000", "http://127.0.0.1:8000"]);
  try {
    origins.add(new URL(apiBaseUrl()).origin);
  } catch {
    /* keep localhost defaults */
  }
  return Array.from(origins).join(" ");
}

function buildCsp(nonce: string): string {
  const scriptSrc = [
    "'self'",
    `'nonce-${nonce}'`,
    "'strict-dynamic'",
    ...(isDev ? ["'unsafe-eval'"] : []),
    "https://www.googletagmanager.com",
    "https://www.google-analytics.com",
    "https://*.googletagmanager.com",
    "https://*.google-analytics.com",
  ].join(" ");

  const connectSrc = [
    "'self'",
    apiConnectOrigins(),
    "https://www.googletagmanager.com",
    "https://*.googletagmanager.com",
    "https://www.google-analytics.com",
    "https://*.google-analytics.com",
    "https://*.analytics.google.com",
    "https://region1.google-analytics.com",
  ].join(" ");

  return [
    "default-src 'self'",
    `script-src ${scriptSrc}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob: https:",
    "font-src 'self' data:",
    `connect-src ${connectSrc}`,
    "frame-src https://www.googletagmanager.com",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join("; ");
}

function applySecurityHeaders(response: NextResponse, nonce: string): NextResponse {
  response.headers.set("Content-Security-Policy", buildCsp(nonce));
  response.headers.set("X-Frame-Options", "DENY");
  response.headers.set("X-Content-Type-Options", "nosniff");
  response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  response.headers.set(
    "Permissions-Policy",
    "camera=(), microphone=(), geolocation=()",
  );
  return response;
}

function newNonce(): string {
  return Buffer.from(crypto.randomUUID()).toString("base64");
}

function isMockMode(): boolean {
  const flag = process.env.NEXT_PUBLIC_USE_MOCK?.trim().toLowerCase();
  return flag === "true" || flag === "1" || flag === "yes";
}

async function lookupProductSlug(id: string): Promise<string | null> {
  if (isMockMode()) return null;
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), PRODUCT_LOOKUP_TIMEOUT_MS);
  try {
    const res = await fetch(catalogProductByIdUrl(apiBaseUrl(), id), {
      method: "GET",
      headers: { Accept: "application/json" },
      signal: ctrl.signal,
      cache: "no-store",
    });
    if (!res.ok) return null;
    const data = (await res.json()) as { slug?: string | null };
    const slug = data.slug?.trim();
    return slug ? slug : null;
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

export async function middleware(request: NextRequest) {
  const nonce = newNonce();
  const numericId = numericProductPathId(request.nextUrl.pathname);

  // ADR-010 / RFC-004: HTTP 301 before Root Layout streams (page-level
  // permanentRedirect becomes meta-refresh once HTML has started).
  if (numericId) {
    const slug = await lookupProductSlug(numericId);
    if (slug && slug !== numericId) {
      const location = new URL(
        encodedProductSlugPath(slug),
        request.nextUrl.origin,
      );
      return applySecurityHeaders(NextResponse.redirect(location, 301), nonce);
    }
  }

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);

  const response = NextResponse.next({
    request: { headers: requestHeaders },
  });
  return applySecurityHeaders(response, nonce);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)"],
};

