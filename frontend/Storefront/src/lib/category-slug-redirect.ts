export {
  CATEGORY_SLUG_REDIRECTS,
  resolveCategorySlugRedirect,
} from "@/config/category-slug-redirects";

export function categoryHubPath(slug: string): string {
  return `/categories/${encodeURIComponent(slug)}`;
}
