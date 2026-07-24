import { Suspense } from "react";
import type { Metadata } from "next";
import { CatalogView } from "@/components/catalog/catalog-view";
import { Container } from "@/components/ui/container";
import { ProductCardSkeleton } from "@/components/product/product-card";

export const metadata: Metadata = {
  title: "فروشگاه ابزار",
  description: "مرور و فیلتر محصولات ابزار صنعتی و تراشکاری کارزار.",
};

/** `useSearchParams` requires a Suspense boundary in the App Router. */
export default function CatalogPage() {
  return (
    <Suspense fallback={<CatalogFallback />}>
      <CatalogView />
    </Suspense>
  );
}

function CatalogFallback() {
  return (
    <Container className="py-10">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <ProductCardSkeleton key={i} />
        ))}
      </div>
    </Container>
  );
}
