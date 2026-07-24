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
import { env } from "@/config/env";
import type { Brand, CategoryFlat, CategoryTreeNode } from "@/types/category";
import type { Article, BlogPost, HeroSlide, ProductComment } from "@/types/content";
import type { SpecFilterOptions } from "@/types/spec-filter";
import type {
  ProductDetail,
  ProductListParams,
  ProductListResponse,
  ProductSummary,
} from "@/types/product";

export const catalogService = {
  async listCategoriesTree(): Promise<CategoryTreeNode[]> {
    if (env.USE_MOCK) return (await getMockApi()).listCategoriesTree();
    const { data } = await apiClient.get<CategoryTreeNode[]>("/categories/tree");
    return data;
  },

  async listCategoriesFlat(): Promise<CategoryFlat[]> {
    if (env.USE_MOCK) return (await getMockApi()).listCategoriesFlat();
    const { data } = await apiClient.get<{ data: CategoryFlat[] }>("/categories/");
    return data.data;
  },

  async listBrands(): Promise<Brand[]> {
    if (env.USE_MOCK) return (await getMockApi()).listBrands();
    const { data } = await apiClient.get<{ data: Brand[] }>("/brands/");
    return data.data;
  },

  async listProducts(params: ProductListParams = {}): Promise<ProductListResponse> {
    if (env.USE_MOCK) return (await getMockApi()).listProducts(params);

    const { spec_filters, brand_ids, countries, ...rest } = params;
    const searchParams = new URLSearchParams();
    for (const [key, value] of Object.entries(rest)) {
      if (value == null || value === "") continue;
      searchParams.set(key, String(value));
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
    return data;
  },

  async getProduct(id: number): Promise<ProductDetail> {
    if (env.USE_MOCK) return (await getMockApi()).getProduct(id);
    const { data } = await apiClient.get<ProductDetail>(`/products/${id}`);
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
    const { data } = await apiClient.get<{ data: Article[] }>("/blog/");
    return data.data;
  },

  async getArticle(slug: string): Promise<BlogPost> {
    if (env.USE_MOCK) return (await getMockApi()).getArticle(slug);
    const { data } = await apiClient.get<BlogPost>(`/blog/${slug}`);
    return data;
  },

  async getProductsByIds(ids: number[]): Promise<ProductSummary[]> {
    if (!ids.length) return [];
    if (env.USE_MOCK) return (await getMockApi()).getProductsByIds(ids);
    const { data } = await apiClient.get<{ data: ProductSummary[] }>("/products/", {
      params: { ids: ids.join(",") },
    });
    return data.data;
  },

  async listHeroSlides(): Promise<HeroSlide[]> {
    if (env.USE_MOCK) return (await getMockApi()).listHeroSlides();
    const { data } = await apiClient.get<{ data: HeroSlide[] }>("/hero-slides/");
    return data.data;
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
    const { data } = await apiClient.get<Brand>(`/brands/slug/${slug}`);
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
