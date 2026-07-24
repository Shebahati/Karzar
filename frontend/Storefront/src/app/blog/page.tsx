import type { Metadata } from "next";
import { BlogList } from "@/components/blog/blog-list";

export const metadata: Metadata = {
  title: "مجله کارزار",
  description: "مقالات تخصصی دنیای ابزار صنعتی و تراشکاری.",
};

export default function BlogPage() {
  return <BlogList />;
}
