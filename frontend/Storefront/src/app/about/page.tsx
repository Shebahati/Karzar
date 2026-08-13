import type { Metadata } from "next";
import { AboutView } from "@/components/about/about-view";
import { INDEXABLE_STATIC_CANONICALS, selfCanonicalAlternates } from "@/lib/crawl-hygiene";

export const metadata: Metadata = {
  title: "درباره ما",
  description: "داستان کارزار؛ مرجع تخصصی ابزارآلات صنعتی و تراشکاری در ایران.",
  alternates: selfCanonicalAlternates(INDEXABLE_STATIC_CANONICALS.about),
};

export default function AboutPage() {
  return <AboutView />;
}
