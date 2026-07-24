/** Allow only same-origin relative paths (block open redirects via //evil.com). */
export function sanitizeNextPath(raw: string | null): string {
  if (!raw) return "/";
  if (!raw.startsWith("/") || raw.startsWith("//")) return "/";
  return raw;
}
