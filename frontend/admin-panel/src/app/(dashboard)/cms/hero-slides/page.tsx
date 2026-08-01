import { redirect } from "next/navigation";

/** Legacy CMS hero-slides CRUD is merged into the visual hero builder. */
export default function HeroSlidesRedirectPage() {
  redirect("/cms/hero-design");
}
