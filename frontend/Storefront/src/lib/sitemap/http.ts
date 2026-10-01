import { NextResponse } from "next/server";
import { SITEMAP_REVALIDATE_SECONDS } from "./constants";
import { SitemapGenerationError } from "./errors";

export const SITEMAP_XML_CONTENT_TYPE = "application/xml; charset=utf-8";

export function sitemapXmlOk(
  body: string,
  headers?: Record<string, string>,
): NextResponse {
  return new NextResponse(body, {
    status: 200,
    headers: {
      "Content-Type": SITEMAP_XML_CONTENT_TYPE,
      "Cache-Control": `public, max-age=0, s-maxage=${SITEMAP_REVALIDATE_SECONDS}, stale-while-revalidate=${SITEMAP_REVALIDATE_SECONDS * 2}`,
      ...headers,
    },
  });
}

export function sitemapXmlNotFound(): NextResponse {
  return new NextResponse("Not Found", { status: 404 });
}

export function sitemapXmlServiceUnavailable(
  cohort: string,
  cause?: unknown,
): NextResponse {
  if (cause) {
    console.error(`[sitemap] cohort=${cohort} generation failed`, cause);
  } else {
    console.error(`[sitemap] cohort=${cohort} generation failed`);
  }
  return new NextResponse("Sitemap temporarily unavailable", {
    status: 503,
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Retry-After": "120",
    },
  });
}

export function handleSitemapRoute(
  cohort: string,
  generate: () => Promise<string> | string,
  observability?: Record<string, string>,
): Promise<NextResponse> {
  return Promise.resolve()
    .then(() => generate())
    .then((body) =>
      sitemapXmlOk(body, {
        ...(observability ?? {}),
      }),
    )
    .catch((error) => {
      if (error instanceof SitemapGenerationError) {
        return sitemapXmlServiceUnavailable(error.cohort, error.cause ?? error);
      }
      return sitemapXmlServiceUnavailable(cohort, error);
    });
}
