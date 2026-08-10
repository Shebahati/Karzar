import { redirect } from "next/navigation";

/** Legacy privacy URL — page content replaced by FAQ. */
export default function PrivacyRedirectPage() {
  redirect("/faq");
}
