import { Suspense } from "react";
import type { Metadata } from "next";
import { BlogList } from "@/components/blog/blog-list";
import { Container } from "@/components/ui/container";
import { Skeleton } from "@/components/ui/skeleton";
import { INDEXABLE_STATIC_CANONICALS, selfCanonicalAlternates } from "@/lib/crawl-hygiene";

export const metadata: Metadata = {
  title: "مجله کارزار",
  description: "مقالات تخصصی دنیای ابزار صنعتی و تراشکاری.",
  alternates: selfCanonicalAlternates(INDEXABLE_STATIC_CANONICALS.blog),
};

function BlogFallback() {
  return (
    <div className="bg-hero-glow">
      <Container className="space-y-8 py-10 lg:py-14">
        <div className="mx-auto max-w-md space-y-3 text-center">
          <Skeleton className="mx-auto h-6 w-24 rounded-full" />
          <Skeleton className="mx-auto h-9 w-72" />
          <Skeleton className="mx-auto h-4 w-56" />
        </div>
        <div className="grid gap-4 lg:grid-cols-12">
          <Skeleton className="h-80 rounded-[1.5rem] lg:col-span-7" />
          <div className="grid gap-4 lg:col-span-5">
            <Skeleton className="h-40 rounded-2xl" />
            <Skeleton className="h-40 rounded-2xl" />
          </div>
        </div>
      </Container>
    </div>
  );
}

export default function BlogPage() {
  return (
    <Suspense fallback={<BlogFallback />}>
      <BlogList />
    </Suspense>
  );
}
