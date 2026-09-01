/**
 * Catalog service facade.
 *
 * Each function checks `env.USE_MOCK`: when true it delegates to the in-memory
 * mock; when false it issues the real HTTP request via the shared Axios client.
 * Components and React Query hooks import only from here and never know which
 * source is active — flipping `NEXT_PUBLIC_USE_MOCK` is the single switch.
 */

import { apiClient } from "@/lib/api-client";
import { getMockApi } from "@/lib/get-mock-api";
import { encodeSlugPathSegment } from "@/lib/product-url";
import { env } from "@/config/env";
import {
  isCategoryIconUrl,
  resolveCategoryIconUrl,
} from "@/config/category-icons";
import type { Brand, CategoryFlat, CategoryTreeNode } from "@/types/category";
import type { Article, BlogPost, HeroSlide, ProductComment } from "@/types/content";
import type { SpecFilterOptions } from "@/types/spec-filter";
import type { NavGroupApiRow } from "@/config/nav-groups";
import {
  isApiProductSort,
  productHasDiscount,
  type ProductDetail,
  type ProductListParams,
  type ProductListResponse,
  type ProductSummary,
} from "@/types/product";

/** Fill missing L1 icon URLs from the designed asset map (live API often omits them). */
function enrichTreeIcons(nodes: CategoryTreeNode[]): CategoryTreeNode[] {
  return nodes.map((node) => {
    const resolved =
      resolveCategoryIconUrl(node) ??
      (isCategoryIconUrl(node.icon) ? node.icon : null);
    return {
      ...node,
      icon: resolved ?? node.icon,
      subcategories: node.subcategories?.length
        ? enrichTreeIcons(node.subcategories)
        : node.subcategories,
    };
  });
}

export const catalogService = {
  async listCategoriesTree(): Promise<CategoryTreeNode[]> {
    if (env.USE_MOCK) return (await getMockApi()).listCategoriesTree();
    const { data } = await apiClient.get<CategoryTreeNode[]>("/categories/tree");
    return enrichTreeIcons(data ?? []);
  },

  async listCategoriesFlat(): Promise<CategoryFlat[]> {
    if (env.USE_MOCK) return (await getMockApi()).listCategoriesFlat();
    const { data } = await apiClient.get<{ data: CategoryFlat[] }>("/categories/");
    return (data.data ?? []).map((row) => {
      if (row.parent_id != null) return row;
      const resolved = resolveCategoryIconUrl(row);
      return resolved ? { ...row, icon: resolved } : row;
    });
  },

  async listBrands(): Promise<Brand[]> {
    if (env.USE_MOCK) return (await getMockApi()).listBrands();
    const { data } = await apiClient.get<{ data: Brand[] }>("/brands/", {
      params: { storefront_product_counts: true },
    });
    return data.data;
  },

  async listProducts(params: ProductListParams = {}): Promise<ProductListResponse> {
    if (env.USE_MOCK) return (await getMockApi()).listProducts(params);

    const { spec_filters, brand_ids, countries, sort, on_sale, ...rest } = params;
    const searchParams = new URLSearchParams();

    // Live API has no on_sale facet — over-fetch then filter client-side when needed.
    const wantLimit = rest.limit ?? 12;
    const wantSkip = rest.skip ?? 0;
    const liveRest = on_sale
      ? { ...rest, skip: 0, limit: Math.min(Math.max(wantLimit * 8, 120), 200) }
      : rest;

    for (const [key, value] of Object.entries(liveRest)) {
      if (value == null || value === "") continue;
      searchParams.set(key, String(value));
    }
    // Only forward OpenAPI-allowed `sort` keys (avoids 422 Invalid sort key).
    if (sort && isApiProductSort(sort)) {
      searchParams.set("sort", sort);
    }
    // FastAPI list query: brand_id=1&brand_id=2 (also accepts comma-separated).
    for (const id of brand_ids ?? []) {
      searchParams.append("brand_id", String(id));
    }
    for (const country of countries ?? []) {
      searchParams.append("country", country);
    }
    if (spec_filters) {
      for (const [path, value] of Object.entries(spec_filters)) {
        if (value) searchParams.set(`spec_${path.replace(/\./g, "__")}`, value);
      }
    }

    const { data } = await apiClient.get<ProductListResponse>(
      `/products/?${searchParams.toString()}`.replace(/\?$/, ""),
    );

    if (!on_sale) return data;

    const discounted = (data.data ?? [])
      .filter((p) => productHasDiscount(p))
      .sort((a, b) => (b.discount_percent ?? 0) - (a.discount_percent ?? 0));
    const page = discounted.slice(wantSkip, wantSkip + wantLimit);
    return {
      data: page,
      meta: {
        total_count: discounted.length,
        skip: wantSkip,
        limit: wantLimit,
        has_next: wantSkip + wantLimit < discounted.length,
        has_prev: wantSkip > 0,
      },
    };
  },

  async getProduct(id: number): Promise<ProductDetail> {
    if (env.USE_MOCK) return (await getMockApi()).getProduct(id);
    const { data } = await apiClient.get<ProductDetail>(`/products/${id}`);
    return data;
  },

  async getProductBySlug(slug: string): Promise<ProductDetail> {
    if (env.USE_MOCK) return (await getMockApi()).getProductBySlug(slug);
    // Decode-once then encode-once: Next may hand a pre-encoded Unicode param.
    const { data } = await apiClient.get<ProductDetail>(
      `/products/slug/${encodeSlugPathSegment(slug)}`,
    );
    return data;
  },

  async getRelatedProducts(id: number): Promise<ProductSummary[]> {
    if (env.USE_MOCK) return (await getMockApi()).getRelatedProducts(id);
    const { data } = await apiClient.get<{ data: ProductSummary[] }>(
      `/products/${id}/related`,
    );
    return data.data;
  },

  async listComments(productId: number): Promise<ProductComment[]> {
    if (env.USE_MOCK) return (await getMockApi()).listComments(productId);
    const { data } = await apiClient.get<{ data: ProductComment[] }>(
      `/products/${productId}/comments`,
    );
    return data.data;
  },

  async listArticles(): Promise<Article[]> {
    if (env.USE_MOCK) return (await getMockApi()).listArticles();
    try {
      const { data } = await apiClient.get<{ data: Article[] }>("/blog/");
      const live = data.data ?? [];
      // Live SoT when populated; empty DB → preview mocks so designs stay testable.
      if (live.length > 0) return live;
    } catch {
      /* fall through to mock preview */
    }
    return (await getMockApi()).listArticles();
  },

  async getArticle(slug: string): Promise<BlogPost> {
    if (env.USE_MOCK) return (await getMockApi()).getArticle(slug);
    try {
      const { data } = await apiClient.get<BlogPost>(`/blog/${slug}`);
      return data;
    } catch {
      // Preview slugs (and empty-CMS local) resolve from mock posts only.
      return (await getMockApi()).getArticle(slug);
    }
  },

  async getProductsByIds(ids: number[]): Promise<ProductSummary[]> {
    if (!ids.length) return [];
    if (env.USE_MOCK) return (await getMockApi()).getProductsByIds(ids);
    const { data } = await apiClient.get<ProductListResponse>("/products/", {
      params: {
        ids: ids.join(","),
        // Default list limit is 100 — without this, long id lists truncate silently.
        limit: Math.min(Math.max(ids.length, 1), 1000),
        skip: 0,
      },
    });
    return data.data ?? [];
  },

  async listHeroSlides(): Promise<HeroSlide[]> {
    if (env.USE_MOCK) return (await getMockApi()).listHeroSlides();
    const { data } = await apiClient.get<{ data: HeroSlide[] }>("/hero-slides/");
    return data.data;
  },

  async listNavGroups(): Promise<NavGroupApiRow[]> {
    if (env.USE_MOCK) return [];
    try {
      const { data } = await apiClient.get<{ data?: NavGroupApiRow[] }>("/nav-groups/");
      const rows = data?.data;
      return Array.isArray(rows) ? rows : [];
    } catch {
      // Network / server error → hardcoded NAV_GROUPS fallback in the query layer.
      return [];
    }
  },

  async getSpecLabels(): Promise<Record<string, string>> {
    if (env.USE_MOCK) return (await getMockApi()).getSpecLabels();
    const { data } = await apiClient.get<{ labels: Record<string, string> }>(
      "/categories/spec-labels",
    );
    return data.labels;
  },

  async getSpecFilterOptions(categoryId: number): Promise<SpecFilterOptions> {
    if (env.USE_MOCK) return (await getMockApi()).getSpecFilterOptions(categoryId);
    const { data } = await apiClient.get<SpecFilterOptions>(
      `/categories/${categoryId}/spec-filter-options`,
    );
    return data;
  },

  async getCategoryBySlug(slug: string): Promise<CategoryFlat> {
    if (env.USE_MOCK) {
      const all = await (await getMockApi()).listCategoriesFlat();
      const found = all.find((c) => c.slug === slug || String(c.id) === slug);
      if (!found) throw new Error("Category not found");
      return found;
    }
    const { data } = await apiClient.get<CategoryFlat>(`/categories/slug/${slug}`);
    return data;
  },

  async getBrandBySlug(slug: string): Promise<Brand> {
    if (env.USE_MOCK) {
      const all = await (await getMockApi()).listBrands();
      const found = all.find((b) => b.slug === slug || String(b.id) === slug);
      if (!found) throw new Error("Brand not found");
      return found;
    }
    const { data } = await apiClient.get<Brand>(`/brands/slug/${slug}`, {
      params: { storefront_product_counts: true },
    });
    return data;
  },

  async createComment(
    productId: number,
    payload: { author_name: string; rating: number; body: string },
  ): Promise<ProductComment> {
    if (env.USE_MOCK) {
      return {
        id: Date.now(),
        product_id: productId,
        author_name: payload.author_name,
        rating: payload.rating,
        body: payload.body,
        created_at: new Date().toISOString(),
        is_verified_buyer: false,
      };
    }
    const { data } = await apiClient.post<ProductComment>(
      `/products/${productId}/comments`,
      payload,
    );
    return data;
  },
};
