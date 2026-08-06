import type { Metadata } from "next";
import { CategoriesIndexView } from "@/components/category/categories-index-view";

export const metadata: Metadata = {
  title: "محصولات",
  description: "دسته‌بندی‌های اصلی ابزار صنعتی کارزار — اندازه‌گیری، براده‌برداری، گیرش و بیشتر.",
};

export default function CategoriesIndexPage() {
  return <CategoriesIndexView />;
}
