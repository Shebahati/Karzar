import type { Metadata } from "next";
import { NOINDEX_NOFOLLOW } from "@/lib/crawl-hygiene";

export const metadata: Metadata = {
  robots: NOINDEX_NOFOLLOW,
};

export default function AccountLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return children;
}
