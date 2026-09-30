export class SitemapNotFoundError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SitemapNotFoundError";
  }
}

export class SitemapGenerationError extends Error {
  readonly cohort: string;

  constructor(cohort: string, message?: string, options?: { cause?: unknown }) {
    super(message ?? `Sitemap generation failed for cohort: ${cohort}`);
    this.name = "SitemapGenerationError";
    this.cohort = cohort;
    if (options?.cause !== undefined) {
      (this as Error & { cause?: unknown }).cause = options.cause;
    }
  }
}
