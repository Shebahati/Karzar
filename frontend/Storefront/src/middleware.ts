import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const isDev = process.env.NODE_ENV !== "production";

function apiConnectOrigins(): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
  const origins = new Set<string>(["http://localhost:8000", "http://127.0.0.1:8000"]);
  try {
    origins.add(new URL(base).origin);
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
    "frame-src https://www.googletagmanager.com https://www.google.com https://maps.google.com https://*.enamad.ir https://trustseal.enamad.ir",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join("; ");
}

export function middleware(request: NextRequest) {
  const nonce = Buffer.from(crypto.randomUUID()).toString("base64");
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);

  const response = NextResponse.next({
    request: { headers: requestHeaders },
  });

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

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)"],
};
