import { NextResponse } from "next/server";

import {
  createAdminSessionValue,
  getAdminSessionSecret,
} from "@/lib/admin-session-token";
import { ADMIN_SESSION_COOKIE } from "@/lib/session-cookie";

export const runtime = "edge";

function apiBase(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
}

function cookieSecure(): boolean {
  return process.env.NODE_ENV === "production";
}

/**
 * Establish a signed HttpOnly edge-session cookie after proving admin auth
 * via Bearer (from login response) or, in mock mode, an explicit mock header.
 */
export async function POST(request: Request) {
  // Touch secret early so misconfig fails closed in production.
  getAdminSessionSecret();

  const useMock =
    (process.env.NEXT_PUBLIC_USE_MOCK ?? "false").toLowerCase() === "true";
  const mockBootstrap = request.headers.get("x-karzar-mock-session") === "1";

  if (useMock && mockBootstrap) {
    const value = await createAdminSessionValue();
    const res = NextResponse.json({ ok: true });
    res.cookies.set(ADMIN_SESSION_COOKIE, value, {
      httpOnly: true,
      secure: cookieSecure(),
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 60 * 24 * 7,
    });
    return res;
  }

  const auth = request.headers.get("authorization");
  if (!auth?.toLowerCase().startsWith("bearer ")) {
    return NextResponse.json({ ok: false, error: "unauthorized" }, { status: 401 });
  }

  let meRes: Response;
  try {
    meRes = await fetch(`${apiBase()}/auth/me`, {
      headers: { Authorization: auth, Accept: "application/json" },
      cache: "no-store",
    });
  } catch {
    return NextResponse.json({ ok: false, error: "upstream" }, { status: 502 });
  }

  if (!meRes.ok) {
    return NextResponse.json({ ok: false, error: "unauthorized" }, { status: 401 });
  }

  const me = (await meRes.json()) as { role?: string; is_active?: boolean };
  if (!me.is_active || me.role !== "super_admin") {
    return NextResponse.json({ ok: false, error: "forbidden" }, { status: 403 });
  }

  const value = await createAdminSessionValue();
  const res = NextResponse.json({ ok: true });
  res.cookies.set(ADMIN_SESSION_COOKIE, value, {
    httpOnly: true,
    secure: cookieSecure(),
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 7,
  });
  return res;
}

export async function DELETE() {
  const res = NextResponse.json({ ok: true });
  res.cookies.set(ADMIN_SESSION_COOKIE, "", {
    httpOnly: true,
    secure: cookieSecure(),
    sameSite: "lax",
    path: "/",
    maxAge: 0,
  });
  return res;
}
