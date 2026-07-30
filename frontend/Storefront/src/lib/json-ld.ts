/**
 * Storefront JSON-LD builders (SEO-001).
 *
 * Rules (aligned with seo-architecture-constitution + Google Product rich results):
 * - Emit Offer only when catalog `base_price` is present (inquiry SKUs → Product without Offer).
 * - Never invent aggregateRating / reviews.
 * - priceCurrency is always IRR; price SoT is catalog `base_price` (not Hesabfa).
 * - Prefer gallery images over thumbnail when available.
 */

import { resolveJsonLdDescription } from "@/lib/product-seo";
import { getSiteUrl } from "@/lib/site-url";
import {
  STORE_ADDRESS_COUNTRY,
  STORE_ADDRESS_FA,
  STORE_ADDRESS_LOCALITY,
  STORE_EMAIL,
  STORE_GEO,
  STORE_MAPS_URL,
  STORE_NAME_FA,
  STORE_PHONE_E164,
} from "@/lib/store-location";
import type { Brand, CategoryFlat } from "@/types/category";
import type { ProductDetail, ProductImage, ProductSummary } from "@/types/product";

/** Re-export for tests / consumers; resolved once at module load (build-time NEXT_PUBLIC_*). */
export const SITE_URL = getSiteUrl();
export const ORG_NAME = STORE_NAME_FA;
export const ORG_ID = `${SITE_URL}/#organization`;
export const WEBSITE_ID = `${SITE_URL}/#website`;

export type JsonLdNode = Record<string, unknown>;

export function wrapJsonLdGraph(nodes: JsonLdNode[]): JsonLdNode {
  return { "@context": "https://schema.org", "@graph": nodes };
}

/** True when catalog base_price is present (priced SKU). Empty/null → inquiry. */
export function hasPresentPrice(basePrice: string | null | undefined): boolean {
  return basePrice != null && String(basePrice).trim() !== "";
}

/** Gallery first (primary sorted ahead), else thumbnail. */
export function resolveProductImages(product: {
  thumbnail?: string | null;
  images?: Pick<ProductImage, "url" | "is_primary">[];
}): string[] | undefined {
  const gallery = [...(product.images ?? [])]
    .filter((img) => Boolean(img.url))
    .sort((a, b) => Number(b.is_primary) - Number(a.is_primary))
    .map((img) => img.url);
  if (gallery.length) return gallery;
  if (product.thumbnail) return [product.thumbnail];
  return undefined;
}

export function productPageUrl(product: {
  id: number;
  slug?: string | null;
}): string {
  const slug = product.slug?.trim();
  if (slug) return `${SITE_URL}/product/${slug}`;
  return `${SITE_URL}/product/${product.id}`;
}

export function categoryPageUrl(slug: string): string {
  return `${SITE_URL}/categories/${slug}`;
}

export function brandPageUrl(slug: string): string {
  return `${SITE_URL}/brands/${slug}`;
}

/**
 * Sitewide org node: Organization + LocalBusiness (same @id) with geo / address / hasMap.
 * Telephone + email mirror contact/footer; openingHours omitted (not published elsewhere).
 */
export function buildOrganizationNode(): JsonLdNode {
  return {
    "@type": ["Organization", "LocalBusiness"],
    "@id": ORG_ID,
    name: ORG_NAME,
    url: SITE_URL,
    logo: `${SITE_URL}/icon.svg`,
    email: STORE_EMAIL,
    telephone: STORE_PHONE_E164,
    hasMap: STORE_MAPS_URL,
    address: {
      "@type": "PostalAddress",
      streetAddress: STORE_ADDRESS_FA,
      addressLocality: STORE_ADDRESS_LOCALITY,
      addressCountry: STORE_ADDRESS_COUNTRY,
    },
    geo: {
      "@type": "GeoCoordinates",
      latitude: STORE_GEO.latitude,
      longitude: STORE_GEO.longitude,
    },
  };
}

/** Sitewide WebSite + optional SearchAction targeting catalog search. */
export function buildWebSiteNode(opts?: { includeSearchAction?: boolean }): JsonLdNode {
  const node: JsonLdNode = {
    "@type": "WebSite",
    "@id": WEBSITE_ID,
    name: ORG_NAME,
    url: SITE_URL,
    inLanguage: "fa-IR",
    publisher: { "@id": ORG_ID },
  };
  if (opts?.includeSearchAction !== false) {
    node.potentialAction = {
      "@type": "SearchAction",
      target: {
        "@type": "EntryPoint",
        urlTemplate: `${SITE_URL}/catalog?search={search_term_string}`,
      },
      "query-input": "required name=search_term_string",
    };
  }
  return node;
}

export function buildSitewideJsonLd(): JsonLdNode {
  return wrapJsonLdGraph([buildOrganizationNode(), buildWebSiteNode()]);
}

export interface BreadcrumbCrumb {
  name: string;
  url?: string;
}

export function buildBreadcrumbList(crumbs: BreadcrumbCrumb[]): JsonLdNode {
  return {
    "@type": "BreadcrumbList",
    itemListElement: crumbs.map((crumb, index) => {
      const item: JsonLdNode = {
        "@type": "ListItem",
        position: index + 1,
        name: crumb.name,
      };
      if (crumb.url) item.item = crumb.url;
      return item;
    }),
  };
}

export function buildPdpBreadcrumbs(product: {
  name: string;
  category?: { name?: string | null; slug?: string | null } | null;
  url: string;
}): BreadcrumbCrumb[] {
  const crumbs: BreadcrumbCrumb[] = [{ name: "خانه", url: SITE_URL }];
  if (product.category?.name) {
    crumbs.push({
      name: product.category.name,
      url: product.category.slug
        ? categoryPageUrl(product.category.slug)
        : undefined,
    });
  }
  crumbs.push({ name: product.name, url: product.url });
  return crumbs;
}

/**
 * Product JSON-LD. Offer is omitted when base_price is null/empty (inquiry SKUs)
 * so Google does not see an invalid Offer without price.
 */
export function buildProductNode(product: ProductDetail): JsonLdNode {
  const url = productPageUrl(product);
  const node: JsonLdNode = {
    "@type": "Product",
    "@id": `${url}#product`,
    name: product.name,
    url,
    sku: product.sku,
    description: resolveJsonLdDescription({
      shortDescription: product.short_description,
      description: product.description,
      name: product.name,
    }),
  };

  const images = resolveProductImages(product);
  if (images?.length) node.image = images;

  if (product.brand?.name) {
    node.brand = { "@type": "Brand", name: product.brand.name };
  }

  if (hasPresentPrice(product.base_price)) {
    node.offers = {
      "@type": "Offer",
      url,
      priceCurrency: "IRR",
      price: String(product.base_price).trim(),
      availability: product.availability
        ? "https://schema.org/InStock"
        : "https://schema.org/OutOfStock",
      itemCondition: "https://schema.org/NewCondition",
      seller: { "@id": ORG_ID },
    };
  }

  return node;
}

export function buildProductPageJsonLd(product: ProductDetail): JsonLdNode {
  const url = productPageUrl(product);
  return wrapJsonLdGraph([
    buildProductNode(product),
    buildBreadcrumbList(buildPdpBreadcrumbs({ ...product, url })),
  ]);
}

export function buildCategoryBreadcrumbs(
  category: CategoryFlat,
  ancestors: CategoryFlat[] = [],
): BreadcrumbCrumb[] {
  const crumbs: BreadcrumbCrumb[] = [
    { name: "خانه", url: SITE_URL },
    { name: "فروشگاه", url: `${SITE_URL}/catalog` },
  ];
  for (const ancestor of ancestors) {
    crumbs.push({
      name: ancestor.name,
      url: ancestor.slug ? categoryPageUrl(ancestor.slug) : undefined,
    });
  }
  crumbs.push({
    name: category.name,
    url: category.slug ? categoryPageUrl(category.slug) : undefined,
  });
  return crumbs;
}

/** CollectionPage + ItemList for category hubs (indexable PLP). */
export function buildCategoryHubJsonLd(opts: {
  category: CategoryFlat;
  ancestors?: CategoryFlat[];
  products: ProductSummary[];
}): JsonLdNode {
  const { category, products } = opts;
  const ancestors = opts.ancestors ?? [];
  const url = category.slug
    ? categoryPageUrl(category.slug)
    : `${SITE_URL}/catalog?category=${category.id}`;

  const itemListElement = products.map((p, index) => ({
    "@type": "ListItem",
    position: index + 1,
    url: productPageUrl(p),
    name: p.name,
  }));

  const collection: JsonLdNode = {
    "@type": "CollectionPage",
    "@id": `${url}#collection`,
    name: category.name,
    url,
    isPartOf: { "@id": WEBSITE_ID },
    mainEntity: {
      "@type": "ItemList",
      "@id": `${url}#itemlist`,
      numberOfItems: products.length,
      itemListElement,
    },
  };

  if (category.meta_description) {
    collection.description = category.meta_description;
  }

  return wrapJsonLdGraph([
    collection,
    buildBreadcrumbList(buildCategoryBreadcrumbs(category, ancestors)),
  ]);
}

/** CollectionPage + Brand for Brand Hub pages (ADR-010 / brand-hub-page-contract §4.4). */
export function buildBrandHubJsonLd(opts: {
  brand: Brand;
  products: ProductSummary[];
}): JsonLdNode {
  const { brand, products } = opts;
  const slug = brand.slug;
  const url = slug ? brandPageUrl(slug) : `${SITE_URL}/catalog?brand=${brand.id}`;

  const itemListElement = products.map((p, index) => ({
    "@type": "ListItem",
    position: index + 1,
    url: productPageUrl(p),
    name: p.name,
  }));

  const brandNode: JsonLdNode = {
    "@type": "Brand",
    "@id": `${url}#brand`,
    name: brand.name,
    url,
  };

  const collection: JsonLdNode = {
    "@type": "CollectionPage",
    "@id": url,
    name: brand.name,
    url,
    isPartOf: { "@id": WEBSITE_ID },
    about: { "@id": `${url}#brand` },
    mainEntity: {
      "@type": "ItemList",
      "@id": `${url}#itemlist`,
      numberOfItems: products.length,
      itemListElement,
    },
  };

  if (brand.meta_description) {
    collection.description = brand.meta_description;
  }

  return wrapJsonLdGraph([
    brandNode,
    collection,
    buildBreadcrumbList([
      { name: "خانه", url: SITE_URL },
      { name: brand.name, url },
    ]),
  ]);
}
