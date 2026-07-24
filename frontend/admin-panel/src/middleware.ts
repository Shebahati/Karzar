import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { ADMIN_SESSION_COOKIE } from "@/lib/session-cookie";
import { verifyAdminSessionValue } from "@/lib/admin-session-token";

const isDev = process.env.NODE_ENV !== "production";

function apiConnectOrigins(): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
  const origins = new Set<string>(["http://localhost:8000", "http://127.0.0.1:8000"]);
  try {
    origins.add(new URL(base).origin);
  } catch {
    /* keep defaults */
  }
  return Array.from(origins).join(" ");
}

function buildCsp(nonce: string): string {
  const scriptSrc = [
    "'self'",
    `'nonce-${nonce}'`,
    "'strict-dynamic'",
    ...(isDev ? ["'unsafe-eval'"] : []),
  ].join(" ");
  return [
    "default-src 'self'",
    `script-src ${scriptSrc}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob: https:",
    "font-src 'self' data:",
    `connect-src 'self' ${apiConnectOrigins()}`,
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join("; ");
}

/**
 * Edge gate for dashboard routes + nonce CSP.
 * Cookie must be HMAC-signed via POST /api/session after /auth/me proves super_admin.
 * AuthGate still verifies API session + role on the client.
 */
export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const nonce = Buffer.from(crypto.randomUUID()).toString("base64");
  const csp = buildCsp(nonce);
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  // Next extracts the nonce from the request CSP during SSR (see Next CSP guide).
  requestHeaders.set("Content-Security-Policy", csp);

  const passThrough = () => {
    const response = NextResponse.next({ request: { headers: requestHeaders } });
    response.headers.set("Content-Security-Policy", csp);
    return response;
  };

  if (
    pathname.startsWith("/login") ||
    pathname.startsWith("/api/session") ||
    pathname.startsWith("/_next") ||
    pathname.startsWith("/favicon") ||
    pathname.includes(".")
  ) {
    return passThrough();
  }

  const raw = request.cookies.get(ADMIN_SESSION_COOKIE)?.value;
  const ok = await verifyAdminSessionValue(raw);
  if (!ok) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname === "/" ? "/" : pathname);
    const res = NextResponse.redirect(url);
    res.headers.set("Content-Security-Policy", csp);
    if (raw) {
      res.cookies.set(ADMIN_SESSION_COOKIE, "", {
        httpOnly: true,
        path: "/",
        maxAge: 0,
      });
    }
    return res;
  }

  return passThrough();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)"],
};
