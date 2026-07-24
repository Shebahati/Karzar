import type { Metadata } from "next";
import { AboutView } from "@/components/about/about-view";

export const metadata: Metadata = {
  title: "درباره ما",
  description: "داستان کارزار؛ مرجع تخصصی ابزارآلات صنعتی و تراشکاری در ایران.",
};

export default function AboutPage() {
  return <AboutView />;
}
