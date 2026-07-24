import type { NextConfig } from "next";

type RemotePattern = {
  protocol: "http" | "https";
  hostname: string;
  port?: string;
  pathname?: string;
};

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

  if (process.env.NODE_ENV !== "production") {
    patterns.push(
      { protocol: "https", hostname: "picsum.photos" },
      { protocol: "https", hostname: "images.unsplash.com" },
    );
  }

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
    /* ignore */
  }

  return patterns;
}

/** Non-CSP headers — CSP (with nonce) is set in middleware.ts */
const securityHeaders = [
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
];

const nextConfig: NextConfig = {
  output: "standalone",
  images: {
    remotePatterns: imageRemotePatterns(),
  },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default nextConfig;
