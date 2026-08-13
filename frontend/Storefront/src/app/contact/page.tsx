import type { Metadata } from "next";
import { ContactView } from "@/components/contact/contact-view";
import { INDEXABLE_STATIC_CANONICALS, selfCanonicalAlternates } from "@/lib/crawl-hygiene";

export const metadata: Metadata = {
  title: "تماس با ما",
  description: "راه‌های ارتباط با فروشگاه ابزار صنعتی کارزار.",
  alternates: selfCanonicalAlternates(INDEXABLE_STATIC_CANONICALS.contact),
};

export default function ContactPage() {
  return <ContactView />;
}
