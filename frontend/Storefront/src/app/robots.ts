import type { MetadataRoute } from "next";
import { ROBOTS_DISALLOW } from "@/lib/crawl-hygiene";
import { getSiteUrl, isSeoIndexable } from "@/lib/site-url";

export default function robots(): MetadataRoute.Robots {
  const site = getSiteUrl();

  if (!isSeoIndexable()) {
    return {
      rules: {
        userAgent: "*",
        disallow: "/",
      },
      host: site,
    };
  }

  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: [...ROBOTS_DISALLOW],
    },
    sitemap: `${site}/sitemap.xml`,
    host: site,
  };
}
