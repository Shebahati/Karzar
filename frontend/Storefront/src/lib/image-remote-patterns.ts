/**
 * Single source of truth for next/image remote host allowlisting.
 * Imported by `next.config.ts` and runtime SafeImage / src guards.
 */

export type ImageRemotePattern = {
  protocol: "http" | "https";
  hostname: string;
  port?: string;
  pathname?: string;
};

/** Local editorial placeholder used by mocks (never remote CDNs like picsum). */
export const LOCAL_PRODUCT_PLACEHOLDER = "/images/placeholders/karzar-editorial.svg";

/** Hosts we never pass to next/image even if later allowlisted by mistake. */
const BLOCKED_IMAGE_HOSTS = new Set(["picsum.photos", "fastly.picsum.photos"]);

function patternKey(p: Pick<ImageRemotePattern, "hostname" | "port">): string {
  return `${p.hostname}:${p.port ?? ""}`;
}

/** Explicit allowlist for next/image — no wildcard hosts. */
export function imageRemotePatterns(): ImageRemotePattern[] {
  const patterns: ImageRemotePattern[] = [
    {
      protocol: "https",
      hostname: "api.karzartools.com",
      pathname: "/static/uploads/**",
    },
    {
      protocol: "http",
      hostname: "localhost",
      port: "8000",
      pathname: "/static/uploads/**",
    },
    {
      protocol: "http",
      hostname: "127.0.0.1",
      port: "8000",
      pathname: "/static/uploads/**",
    },
  ];

  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
  try {
    const url = new URL(apiBase);
    const protocol = url.protocol === "http:" ? "http" : "https";
    const already = patterns.some((p) => patternKey(p) === patternKey({ hostname: url.hostname, port: url.port || undefined }));
    if (!already && url.hostname) {
      patterns.push({
        protocol,
        hostname: url.hostname,
        ...(url.port ? { port: url.port } : {}),
        pathname: "/static/uploads/**",
      });
    }
  } catch {
    /* ignore invalid env */
  }

  const assetBase = process.env.NEXT_PUBLIC_ASSET_BASE_URL;
  if (assetBase) {
    try {
      const url = new URL(assetBase);
      const protocol = url.protocol === "http:" ? "http" : "https";
      const already = patterns.some((p) => patternKey(p) === patternKey({ hostname: url.hostname, port: url.port || undefined }));
      if (!already && url.hostname) {
        patterns.push({
          protocol,
          hostname: url.hostname,
          ...(url.port ? { port: url.port } : {}),
          pathname: "/static/uploads/**",
        });
      }
    } catch {
      /* ignore */
    }
  }

  return patterns;
}

function pathMatches(pathname: string, pattern?: string): boolean {
  if (!pattern || pattern === "/**") return true;
  if (pattern.endsWith("/**")) {
    const prefix = pattern.slice(0, -3);
    return pathname === prefix || pathname.startsWith(`${prefix}/`);
  }
  return pathname === pattern;
}

function remoteSrcAllowed(url: URL, patterns: ImageRemotePattern[]): boolean {
  const protocol = url.protocol === "http:" ? "http" : url.protocol === "https:" ? "https" : null;
  if (!protocol) return false;
  const host = url.hostname.toLowerCase();
  const port = url.port;

  return patterns.some((p) => {
    if (p.protocol !== protocol) return false;
    if (p.hostname.toLowerCase() !== host) return false;
    if (p.port != null && p.port !== "" && p.port !== port) return false;
    if ((p.port == null || p.port === "") && port) {
      // Pattern without port only matches default scheme ports (empty URL.port).
      return false;
    }
    return pathMatches(url.pathname, p.pathname);
  });
}

/**
 * Returns a src safe for `next/image`, or null when the host is unconfigured /
 * blocked (caller should show ProductPlaceholder instead of crashing).
 */
export function toSafeNextImageSrc(src: string | null | undefined): string | null {
  if (src == null) return null;
  const trimmed = String(src).trim();
  if (!trimmed) return null;

  // Same-origin / public assets
  if (trimmed.startsWith("/") && !trimmed.startsWith("//")) {
    return trimmed;
  }

  let url: URL;
  try {
    url = new URL(trimmed);
  } catch {
    return null;
  }

  if (url.protocol !== "http:" && url.protocol !== "https:") return null;

  const host = url.hostname.toLowerCase();
  if (BLOCKED_IMAGE_HOSTS.has(host) || [...BLOCKED_IMAGE_HOSTS].some((b) => host.endsWith(`.${b}`))) {
    return null;
  }

  if (!remoteSrcAllowed(url, imageRemotePatterns())) return null;

  return trimmed;
}

export function isSafeNextImageSrc(src: string | null | undefined): boolean {
  return toSafeNextImageSrc(src) != null;
}
