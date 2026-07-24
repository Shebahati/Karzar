import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/account/", "/checkout/", "/cart", "/login", "/quote"],
    },
    sitemap: "https://www.karzartools.com/sitemap.xml",
    host: "https://www.karzartools.com",
  };
}
