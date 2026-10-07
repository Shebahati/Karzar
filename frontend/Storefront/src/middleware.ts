import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { categoryHubPath, resolveCategorySlugRedirect } from "@/lib/category-slug-redirect";
import {
  lookupProductSlugForMiddleware,
  middlewareCatalogApiBaseUrl,
} from "@/lib/middleware-product-slug-lookup";
import { encodedProductSlugPath, numericProductPathId } from "@/lib/product-url";

const isDev = process.env.NODE_ENV !== "production";

function apiConnectOrigins(): string {
  const origins = new Set<string>(["http://localhost:8000", "http://127.0.0.1:8000"]);
  try {
    origins.add(new URL(middlewareCatalogApiBaseUrl()).origin);
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

function applySecurityHeaders(response: NextResponse, csp: string): NextResponse {
  response.headers.set("Content-Security-Policy", csp);
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

function categoryPathSlug(pathname: string): string | null {
  const match = pathname.match(/^\/categories\/([^/]+)\/?$/);
  if (!match) return null;
  try {
    return decodeURIComponent(match[1]);
  } catch {
    return null;
  }
}

export async function middleware(request: NextRequest) {
  const nonce = newNonce();
  const csp = buildCsp(nonce);

  const categorySlug = categoryPathSlug(request.nextUrl.pathname);
  if (categorySlug) {
    const targetSlug = resolveCategorySlugRedirect(categorySlug);
    if (targetSlug && targetSlug !== categorySlug) {
      const location = new URL(categoryHubPath(targetSlug), request.nextUrl.origin);
      location.search = request.nextUrl.search;
      return applySecurityHeaders(NextResponse.redirect(location, 301), csp);
    }
  }

  const numericId = numericProductPathId(request.nextUrl.pathname);

  // ADR-010 / RFC-004: HTTP 301 before Root Layout streams (page-level
  // permanentRedirect becomes meta-refresh once HTML has started).
  if (numericId) {
    const slug = await lookupProductSlugForMiddleware(numericId);
    if (slug && slug !== numericId) {
      const location = new URL(encodedProductSlugPath(slug), request.nextUrl.origin);
      location.search = request.nextUrl.search;
      return applySecurityHeaders(NextResponse.redirect(location, 301), csp);
    }
  }

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("Content-Security-Policy", csp);

  const response = NextResponse.next({
    request: { headers: requestHeaders },
  });
  return applySecurityHeaders(response, csp);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)"],
};
