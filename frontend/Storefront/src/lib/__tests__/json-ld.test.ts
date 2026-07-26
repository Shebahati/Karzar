import { describe, expect, it } from "vitest";
import {
  SITE_URL,
  buildCategoryHubJsonLd,
  buildProductNode,
  buildProductPageJsonLd,
  buildSitewideJsonLd,
  hasPresentPrice,
  resolveProductImages,
} from "@/lib/json-ld";
import type { CategoryFlat } from "@/types/category";
import type { ProductDetail, ProductSummary } from "@/types/product";

function baseProduct(overrides: Partial<ProductDetail> = {}): ProductDetail {
  return {
    id: 42,
    sku: "INS-1108",
    name: "کولیس دیجیتال اینسایز",
    category_id: 1,
    brand_id: 1,
    category: { id: 1, name: "کولیس", slug: "caliper" },
    brand: { id: 1, name: "INSIZE" },
    base_price: "1250000",
    original_price: null,
    discount_percent: null,
    stock_quantity: "1",
    stock_unit: "piece",
    stock_status: "in_stock",
    low_stock: false,
    availability: true,
    warranty_text: null,
    weight_grams: null,
    is_original: true,
    tax_percent: "9",
    is_active: true,
    pdf_catalog_url: null,
    thumbnail: "https://cdn.example/thumb.jpg",
    images: [],
    short_description: "کولیس دیجیتال دقت ۰٫۰۱ میلی‌متر",
    description: "توضیحات بلند محصول برای تست.",
    meta_title: null,
    meta_description: null,
    specifications: { technical_specs: [], dimensions: [], features: {} },
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("hasPresentPrice", () => {
  it("accepts non-empty catalog prices", () => {
    expect(hasPresentPrice("1250000")).toBe(true);
    expect(hasPresentPrice("0")).toBe(true);
  });

  it("rejects null/empty inquiry prices", () => {
    expect(hasPresentPrice(null)).toBe(false);
    expect(hasPresentPrice(undefined)).toBe(false);
    expect(hasPresentPrice("")).toBe(false);
    expect(hasPresentPrice("   ")).toBe(false);
  });
});

describe("resolveProductImages", () => {
  it("prefers gallery with primary first", () => {
    const images = resolveProductImages({
      thumbnail: "https://cdn.example/thumb.jpg",
      images: [
        { url: "https://cdn.example/b.jpg", is_primary: false },
        { url: "https://cdn.example/a.jpg", is_primary: true },
      ],
    });
    expect(images).toEqual([
      "https://cdn.example/a.jpg",
      "https://cdn.example/b.jpg",
    ]);
  });

  it("falls back to thumbnail when gallery empty", () => {
    expect(
      resolveProductImages({
        thumbnail: "https://cdn.example/thumb.jpg",
        images: [],
      }),
    ).toEqual(["https://cdn.example/thumb.jpg"]);
  });
});

describe("buildProductNode / Offer gating", () => {
  it("emits Offer with IRR price when base_price is present", () => {
    const node = buildProductNode(baseProduct());
    expect(node["@type"]).toBe("Product");
    expect(node.url).toBe(`${SITE_URL}/product/42`);
    expect(node.offers).toMatchObject({
      "@type": "Offer",
      priceCurrency: "IRR",
      price: "1250000",
      availability: "https://schema.org/InStock",
    });
    expect(node).not.toHaveProperty("aggregateRating");
    expect(node).not.toHaveProperty("review");
  });

  it("omits Offer for inquiry SKUs (null base_price)", () => {
    const node = buildProductNode(baseProduct({ base_price: null }));
    expect(node["@type"]).toBe("Product");
    expect(node.url).toBe(`${SITE_URL}/product/42`);
    expect(node.offers).toBeUndefined();
  });

  it("uses gallery images on Product when available", () => {
    const node = buildProductNode(
      baseProduct({
        images: [
          { id: 1, url: "https://cdn.example/g1.jpg", is_primary: true },
          { id: 2, url: "https://cdn.example/g2.jpg", is_primary: false },
        ],
      }),
    );
    expect(node.image).toEqual([
      "https://cdn.example/g1.jpg",
      "https://cdn.example/g2.jpg",
    ]);
  });
});

describe("buildProductPageJsonLd", () => {
  it("includes Product + BreadcrumbList graph", () => {
    const doc = buildProductPageJsonLd(baseProduct());
    const graph = doc["@graph"] as Record<string, unknown>[];
    expect(doc["@context"]).toBe("https://schema.org");
    expect(graph.map((n) => n["@type"])).toEqual(["Product", "BreadcrumbList"]);
    const crumbs = (graph[1].itemListElement as { name: string }[]).map(
      (c) => c.name,
    );
    expect(crumbs).toEqual(["خانه", "کولیس", "کولیس دیجیتال اینسایز"]);
  });
});

describe("buildSitewideJsonLd", () => {
  it("emits Organization + WebSite with SearchAction", () => {
    const doc = buildSitewideJsonLd();
    const graph = doc["@graph"] as Record<string, unknown>[];
    expect(graph.map((n) => n["@type"])).toEqual(["Organization", "WebSite"]);
    const website = graph[1];
    expect(website.potentialAction).toMatchObject({
      "@type": "SearchAction",
      target: {
        urlTemplate: `${SITE_URL}/catalog?search={search_term_string}`,
      },
    });
  });
});

describe("buildCategoryHubJsonLd", () => {
  it("emits CollectionPage with ItemList + breadcrumbs", () => {
    const category: CategoryFlat = {
      id: 10,
      name: "کولیس دیجیتال",
      slug: "digital-caliper",
      parent_id: 1,
      depth: 2,
      is_leaf: true,
      is_selectable: true,
      breadcrumb: ["ابزار اندازه‌گیری", "کولیس", "کولیس دیجیتال"],
      ancestor_ids: [1, 2],
      meta_description: "مجموعه کولیس دیجیتال صنعتی",
    };
    const ancestors: CategoryFlat[] = [
      {
        id: 1,
        name: "ابزار اندازه‌گیری",
        slug: "metrology",
        parent_id: null,
        depth: 0,
        is_leaf: false,
        is_selectable: false,
        breadcrumb: ["ابزار اندازه‌گیری"],
        ancestor_ids: [],
      },
      {
        id: 2,
        name: "کولیس",
        slug: "caliper",
        parent_id: 1,
        depth: 1,
        is_leaf: false,
        is_selectable: false,
        breadcrumb: ["ابزار اندازه‌گیری", "کولیس"],
        ancestor_ids: [1],
      },
    ];
    const products: ProductSummary[] = [
      {
        id: 42,
        sku: "A",
        name: "محصول الف",
        thumbnail: null,
        base_price: "100",
        stock_status: "in_stock",
        availability: true,
        is_original: true,
        category: null,
        brand: null,
      },
    ];

    const doc = buildCategoryHubJsonLd({ category, ancestors, products });
    const graph = doc["@graph"] as Record<string, unknown>[];
    expect(graph.map((n) => n["@type"])).toEqual([
      "CollectionPage",
      "BreadcrumbList",
    ]);
    const collection = graph[0];
    expect(collection.url).toBe(`${SITE_URL}/categories/digital-caliper`);
    const main = collection.mainEntity as Record<string, unknown>;
    expect(main["@type"]).toBe("ItemList");
    expect(main.numberOfItems).toBe(1);
  });
});
