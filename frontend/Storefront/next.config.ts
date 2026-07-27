import type { NextConfig } from "next";

type RemotePattern = {
  protocol: "http" | "https";
  hostname: string;
  port?: string;
  pathname?: string;
};

/** Explicit allowlist for next/image — no wildcard hosts. */
function imageRemotePatterns(): RemotePattern[] {
  const patterns: RemotePattern[] = [
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
    const already = patterns.some(
      (p) => p.hostname === url.hostname && (p.port ?? "") === (url.port ?? ""),
    );
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
      const already = patterns.some(
        (p) => p.hostname === url.hostname && (p.port ?? "") === (url.port ?? ""),
      );
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

/** Non-CSP headers only — CSP (with nonce) is set in middleware.ts */
const securityHeaders = [
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
];

const nextConfig: NextConfig = {
  output: "standalone",
  images: {
    // Prefer modern codecs; keep 90/100 allowlisted for rare curated stills.
    formats: ["image/avif", "image/webp"],
    qualities: [75, 90, 100],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920],
    imageSizes: [64, 96, 128, 256, 384],
    minimumCacheTTL: 60 * 60 * 24 * 30,
    remotePatterns: imageRemotePatterns(),
  },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default nextConfig;
