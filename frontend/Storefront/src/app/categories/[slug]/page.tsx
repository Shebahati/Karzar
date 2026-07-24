import { Suspense } from "react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { CategoryHubView } from "@/components/category/category-hub-view";
import { Container } from "@/components/ui/container";
import { ProductCardSkeleton } from "@/components/product/product-card";
import { catalogService } from "@/services/catalog";

type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  try {
    const category = await catalogService.getCategoryBySlug(slug);
    const title = category.meta_title || `${category.name} | کارزار`;
    const description =
      category.meta_description ||
      `خرید و مشاهده محصولات دسته ${category.name} در فروشگاه ابزار صنعتی کارزار.`;
    return {
      title,
      description,
      alternates: { canonical: `/categories/${category.slug ?? slug}` },
      openGraph: { title, description, type: "website" },
    };
  } catch {
    return { title: "دسته یافت نشد | کارزار" };
  }
}

export default async function CategoryHubPage({ params }: Props) {
  const { slug } = await params;
  let category;
  try {
    category = await catalogService.getCategoryBySlug(slug);
  } catch {
    notFound();
  }

  return (
    <Suspense
      fallback={
        <Container className="py-10">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <ProductCardSkeleton key={i} />
            ))}
          </div>
        </Container>
      }
    >
      <CategoryHubView category={category} />
    </Suspense>
  );
}
