import type { Metadata } from "next";
import { ContactView } from "@/components/contact/contact-view";

export const metadata: Metadata = {
  title: "تماس با ما",
  description: "راه‌های ارتباط با فروشگاه ابزار صنعتی کارزار.",
};

export default function ContactPage() {
  return <ContactView />;
}
