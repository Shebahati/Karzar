import type { Metadata } from "next";
import { CategoriesIndexView } from "@/components/category/categories-index-view";
import { INDEXABLE_STATIC_CANONICALS, selfCanonicalAlternates } from "@/lib/crawl-hygiene";

export const metadata: Metadata = {
  title: "محصولات",
  description: "دسته‌بندی‌های اصلی ابزار صنعتی کارزار — اندازه‌گیری، براده‌برداری، گیرش و بیشتر.",
  alternates: selfCanonicalAlternates(INDEXABLE_STATIC_CANONICALS.categories),
};

export default function CategoriesIndexPage() {
  return <CategoriesIndexView />;
}
