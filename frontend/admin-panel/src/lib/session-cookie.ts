/** Edge session cookie name — value is HMAC-signed (see admin-session-token.ts). */

export const ADMIN_SESSION_COOKIE = "karzar_admin_session";

/**
 * Ask the Next.js route handler to set a signed HttpOnly session cookie.
 * Live: requires Bearer from login. Mock: bootstrap header (USE_MOCK only).
 */
export async function setAdminSessionCookie(accessToken?: string | null): Promise<void> {
  if (typeof window === "undefined") return;

  const headers: Record<string, string> = {};
  const useMock =
    (process.env.NEXT_PUBLIC_USE_MOCK ?? "false").toLowerCase() === "true";

  if (useMock) {
    headers["x-karzar-mock-session"] = "1";
  } else if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  } else {
    return;
  }

  const res = await fetch("/api/session", {
    method: "POST",
    headers,
    credentials: "same-origin",
  });
  if (!res.ok) {
    throw new Error("ADMIN_SESSION_BOOTSTRAP_FAILED");
  }
}

export async function clearAdminSessionCookie(): Promise<void> {
  if (typeof window === "undefined") return;
  try {
    await fetch("/api/session", {
      method: "DELETE",
      credentials: "same-origin",
    });
  } catch {
    // Best-effort; middleware will bounce if cookie remains invalid.
  }
}
