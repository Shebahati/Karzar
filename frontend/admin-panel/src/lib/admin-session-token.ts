/**
 * HMAC-signed admin edge session (HttpOnly cookie on the admin origin).
 * Not a substitute for API auth — AuthGate + /auth/me remain authoritative.
 */

const encoder = new TextEncoder();

function bufferToHex(buffer: ArrayBuffer): string {
  return Array.from(new Uint8Array(buffer))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export function getAdminSessionSecret(): string {
  const secret =
    process.env.ADMIN_SESSION_SECRET?.trim() ||
    process.env.SESSION_SIGNING_SECRET?.trim() ||
    "";
  if (secret.length >= 32) return secret;
  if (process.env.NODE_ENV === "production") {
    throw new Error("ADMIN_SESSION_SECRET (min 32 chars) is required in production");
  }
  // Dev-only fallback — still blocks trivial `=1` forgery.
  return "karzar-admin-dev-session-secret-change-me!!";
}

async function importKey(secret: string): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign", "verify"],
  );
}

export async function createAdminSessionValue(ttlSeconds = 60 * 60 * 24 * 7): Promise<string> {
  const exp = Math.floor(Date.now() / 1000) + ttlSeconds;
  const nonce = crypto.randomUUID().replace(/-/g, "");
  const payload = `${exp}.${nonce}`;
  const key = await importKey(getAdminSessionSecret());
  const sig = bufferToHex(await crypto.subtle.sign("HMAC", key, encoder.encode(payload)));
  return `${payload}.${sig}`;
}

export async function verifyAdminSessionValue(value: string | undefined | null): Promise<boolean> {
  if (!value) return false;
  const parts = value.split(".");
  if (parts.length !== 3) return false;
  const [expRaw, nonce, sig] = parts;
  if (!expRaw || !nonce || !sig) return false;
  const exp = Number(expRaw);
  if (!Number.isFinite(exp) || exp * 1000 < Date.now()) return false;
  if (!/^[a-f0-9]{64}$/i.test(sig) || !/^[a-f0-9]+$/i.test(nonce)) return false;

  const payload = `${expRaw}.${nonce}`;
  const key = await importKey(getAdminSessionSecret());
  const expected = bufferToHex(await crypto.subtle.sign("HMAC", key, encoder.encode(payload)));
  if (expected.length !== sig.length) return false;
  // Constant-time-ish compare
  let diff = 0;
  for (let i = 0; i < expected.length; i++) {
    diff |= expected.charCodeAt(i) ^ sig.charCodeAt(i);
  }
  return diff === 0;
}
