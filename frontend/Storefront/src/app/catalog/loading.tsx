import { Container } from "@/components/ui/container";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * Catalog-only loading UI.
 *
 * Do NOT place loading.tsx at `app/` root: a root Suspense boundary streams the
 * shell with HTTP 200 before `notFound()` can set a true 404 (Next.js soft-404).
 * Entity routes (/product|/categories|/brands|/blog) must remain outside this.
 */
export default function CatalogLoading() {
  return (
    <Container className="space-y-6 py-10">
      <Skeleton className="h-10 w-48" />
      <Skeleton className="h-40 w-full" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    </Container>
  );
}
