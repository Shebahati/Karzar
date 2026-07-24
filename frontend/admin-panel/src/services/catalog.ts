/**

 * Catalog data-access facade.

 *

 * Every hook calls through this module. When `env.USE_MOCK` is true the calls

 * resolve against the in-memory mock; otherwise they hit the real FastAPI

 * endpoints via the shared axios client. The return shapes are identical, so

 * flipping the flag requires no changes upstream.

 */

import { apiClient, withStepUp } from "@/lib/api-client";

import { getMockApi } from "@/lib/get-mock-api";

import { env } from "@/config/env";

import { flattenCategoryTree } from "@/features/catalog/utils/category-tree";

import type { StepUpTokenResponse } from "@/types/auth";

import type {

  Brand,

  BrandCreatePayload,

  BrandUpdatePayload,

  CategoryCreatePayload,

  CategoryDeleteResult,

  CategoryFlat,

  CategoryTreeNode,

  CategoryUpdatePayload,

} from "@/types/category";

import type { CategorySpecTemplate } from "@/types/spec-template";

import type {

  BulkStockAdjustItem,

  BulkStockAdjustResponse,

  ProductChangeLogListResponse,

  ProductCreatePayload,

  ProductDetail,

  ProductListParams,

  ProductListResponse,

  ProductStatisticsResponse,

  ProductUpdatePayload,

} from "@/types/product";



export const catalogService = {

  async listProducts(params: ProductListParams = {}): Promise<ProductListResponse> {

    if (env.USE_MOCK) return (await getMockApi()).listProducts(params);

    const { data } = await apiClient.get<ProductListResponse>("/products/", { params });

    return data;

  },



  async getProduct(id: number): Promise<ProductDetail> {

    if (env.USE_MOCK) return (await getMockApi()).getProduct(id);

    const { data } = await apiClient.get<ProductDetail>(`/products/${id}`);

    return data;

  },



  async createProduct(payload: ProductCreatePayload): Promise<ProductDetail> {

    if (env.USE_MOCK) return (await getMockApi()).createProduct(payload);

    const { data } = await apiClient.post<ProductDetail>("/products/", payload);

    return data;

  },



  async updateProduct(id: number, payload: ProductUpdatePayload): Promise<ProductDetail> {

    if (env.USE_MOCK) return (await getMockApi()).updateProduct(id, payload);

    const { data } = await apiClient.put<ProductDetail>(`/products/${id}`, payload);

    return data;

  },



  async deleteProduct(id: number, stepUpToken: string): Promise<void> {

    if (env.USE_MOCK) return (await getMockApi()).deleteProduct(id, stepUpToken);

    await apiClient.delete(`/products/${id}`, withStepUp(stepUpToken));

  },



  async listCategories(): Promise<CategoryTreeNode[]> {

    if (env.USE_MOCK) return (await getMockApi()).listCategories();

    const { data } = await apiClient.get<CategoryTreeNode[] | { data: CategoryTreeNode[] }>(
      "/categories/tree",
    );

    return Array.isArray(data) ? data : (data.data ?? []);

  },



  async listFlatCategories(): Promise<CategoryFlat[]> {

    if (env.USE_MOCK) return (await getMockApi()).listFlatCategories();

    try {

      const { data } = await apiClient.get<{ data: CategoryFlat[] }>("/categories/");

      return data.data ?? [];

    } catch {

      const { data } = await apiClient.get<{ data: CategoryTreeNode[] }>("/categories/tree");

      return flattenCategoryTree(data.data ?? []);

    }

  },



  async createCategory(payload: CategoryCreatePayload): Promise<CategoryFlat> {

    if (env.USE_MOCK) return (await getMockApi()).createCategory(payload);

    const { data } = await apiClient.post<CategoryFlat>("/categories/", payload);

    return data;

  },



  async updateCategory(id: number, payload: CategoryUpdatePayload): Promise<CategoryFlat> {

    if (env.USE_MOCK) return (await getMockApi()).updateCategory(id, payload);

    const { data } = await apiClient.put<CategoryFlat>(`/categories/${id}`, payload);

    return data;

  },



  async deleteCategory(
    id: number,
    stepUpToken: string,
    targetCategoryId?: number,
  ): Promise<CategoryDeleteResult> {

    if (env.USE_MOCK) return (await getMockApi()).deleteCategory(id, stepUpToken);

    const { data } = await apiClient.delete<CategoryDeleteResult>(
      `/categories/${id}`,
      withStepUp(stepUpToken, {
        params:
          targetCategoryId != null
            ? { target_category_id: targetCategoryId }
            : undefined,
      }),
    );

    return data;

  },



  async getCategorySpecTemplate(categoryId: number): Promise<CategorySpecTemplate> {

    if (env.USE_MOCK) return (await getMockApi()).getCategorySpecTemplate(categoryId);

    const { data } = await apiClient.get<CategorySpecTemplate>(

      `/categories/${categoryId}/spec-templates`,

    );

    return data;

  },



  async listBrands(): Promise<Brand[]> {

    if (env.USE_MOCK) return (await getMockApi()).listBrands();

    const { data } = await apiClient.get<{ data: Brand[] } | Brand[]>("/brands/");

    return Array.isArray(data) ? data : (data.data ?? []);

  },



  async createBrand(payload: BrandCreatePayload): Promise<Brand> {

    if (env.USE_MOCK) return (await getMockApi()).createBrand(payload);

    const { data } = await apiClient.post<Brand>("/brands/", payload);

    return data;

  },



  async updateBrand(id: number, payload: BrandUpdatePayload): Promise<Brand> {

    if (env.USE_MOCK) return (await getMockApi()).updateBrand(id, payload);

    const { data } = await apiClient.put<Brand>(`/brands/${id}`, payload);

    return data;

  },



  async deleteBrand(id: number, stepUpToken: string): Promise<import("@/types/category").BrandDeleteResult> {

    if (env.USE_MOCK) return (await getMockApi()).deleteBrand(id, stepUpToken);

    const { data } = await apiClient.delete<import("@/types/category").BrandDeleteResult>(

      `/brands/${id}`,

      withStepUp(stepUpToken),

    );

    return data;

  },



  async restoreProduct(id: number, stepUpToken?: string): Promise<ProductDetail> {

    if (env.USE_MOCK) return (await getMockApi()).restoreProduct(id);

    const { data } = await apiClient.post<ProductDetail>(

      `/products/${id}/restore`,

      undefined,

      stepUpToken ? withStepUp(stepUpToken) : undefined,

    );

    return data;

  },



  async getProductBySku(sku: string): Promise<ProductDetail> {

    if (env.USE_MOCK) return (await getMockApi()).getProductBySku(sku);

    const { data } = await apiClient.get<ProductDetail>(`/products/sku/${encodeURIComponent(sku)}`);

    return data;

  },



  async getProductStock(id: number): Promise<import("@/types/product").ProductStockInfo> {
    if (env.USE_MOCK) return (await getMockApi()).getProductStock(id);
    const { data } = await apiClient.get<{
      product_id: number;
      sku?: string;
      stock_quantity: string | number;
      stock_status: string;
    }>(`/products/${id}/stock`);
    const qty = String(data.stock_quantity);
    return {
      product_id: data.product_id,
      sku: data.sku,
      stock_quantity: qty,
      stock_status: data.stock_status,
      quantity: qty,
      low_stock: data.stock_status === "low_stock",
      availability: data.stock_status !== "out_of_stock",
    };
  },

  async adjustProductStock(
    id: number,
    payload: import("@/types/product").ProductStockAdjustPayload,
  ): Promise<import("@/types/product").ProductStockInfo> {
    if (env.USE_MOCK) return (await getMockApi()).adjustProductStock(id, payload);
    // Backend returns ProductDetailResponse from stock/adjust.
    const { data } = await apiClient.post<{
      id: number;
      sku: string;
      stock_quantity: string;
      stock_status: string;
      stock_unit: string;
      low_stock: boolean;
      availability: boolean;
    }>(`/products/${id}/stock/adjust`, null, {
      params: { quantity_delta: payload.delta, reason: payload.reason ?? undefined },
    });
    return {
      product_id: data.id,
      sku: data.sku,
      stock_quantity: data.stock_quantity,
      stock_status: data.stock_status,
      quantity: data.stock_quantity,
      unit: data.stock_unit as import("@/types/product").StockUnit,
      low_stock: data.low_stock,
      availability: data.availability,
    };
  },



  async getProductsByIds(ids: number[]): Promise<import("@/types/product").ProductSummary[]> {

    if (!ids.length) return [];

    if (env.USE_MOCK) return (await getMockApi()).getProductsByIds(ids);

    const { data } = await apiClient.get<{ data: import("@/types/product").ProductSummary[] }>(

      "/products/",

      { params: { ids: ids.join(",") } },

    );

    return data.data ?? [];

  },



  async addProductImageByUrl(

    id: number,

    imageUrl: string,

    isPrimary = false,

  ): Promise<ProductDetail> {

    if (env.USE_MOCK) return (await getMockApi()).addProductImageByUrl(id, imageUrl, isPrimary);

    const { data } = await apiClient.post<ProductDetail>(`/products/${id}/images`, {

      image_url: imageUrl,

      is_primary: isPrimary,

    });

    return data;

  },



  async setPrimaryProductImage(productId: number, imageId: number): Promise<ProductDetail> {

    if (env.USE_MOCK) return (await getMockApi()).setPrimaryProductImage(productId, imageId);

    const { data } = await apiClient.patch<ProductDetail>(

      `/products/${productId}/images/${imageId}/primary`,

    );

    return data;

  },



  async reorderProductImages(

    productId: number,

    imageIds: number[],

  ): Promise<ProductDetail> {

    if (env.USE_MOCK) return (await getMockApi()).reorderProductImages(productId, imageIds);

    const { data } = await apiClient.patch<ProductDetail>(

      `/products/${productId}/images/reorder`,

      { image_ids: imageIds },

    );

    return data;

  },



  async uploadProductImage(

    id: number,

    file: File,

  ): Promise<import("@/types/product").ProductImageUploadResponse> {

    if (env.USE_MOCK) return (await getMockApi()).uploadProductImage(id, file);

    const form = new FormData();

    form.append("file", file);

    const { data } = await apiClient.post<import("@/types/product").ProductImageUploadResponse>(

      `/products/${id}/images`,

      form,

      { headers: { "Content-Type": "multipart/form-data" } },

    );

    return data;

  },



  async deleteProductImage(productId: number, imageId: number): Promise<void> {

    if (env.USE_MOCK) return (await getMockApi()).deleteProductImage(productId, imageId);

    await apiClient.delete(`/products/${productId}/images/${imageId}`);

  },



  async verifyPin(pin: string): Promise<StepUpTokenResponse> {

    if (env.USE_MOCK) return (await getMockApi()).verifyPin(pin);

    const { data } = await apiClient.post<StepUpTokenResponse>("/auth/verify-pin", { pin });

    return data;

  },

  async getStatistics(): Promise<ProductStatisticsResponse> {
    if (env.USE_MOCK) return (await getMockApi()).getProductStatistics();
    const { data } = await apiClient.get<ProductStatisticsResponse>("/products/statistics");
    return data;
  },

  async getChangeLog(
    productId: number,
    params: { skip?: number; limit?: number } = {},
  ): Promise<ProductChangeLogListResponse> {
    if (env.USE_MOCK) return (await getMockApi()).getProductChangeLog(productId, params);
    const { data } = await apiClient.get<ProductChangeLogListResponse>(
      `/products/${productId}/change-log`,
      { params },
    );
    return data;
  },

  async bulkStockAdjust(
    items: BulkStockAdjustItem[],
    stepUpToken: string,
  ): Promise<BulkStockAdjustResponse> {
    if (env.USE_MOCK) return (await getMockApi()).bulkStockAdjust(items);
    const { data } = await apiClient.post<BulkStockAdjustResponse>(
      "/products/bulk/stock-adjust",
      { items },
      withStepUp(stepUpToken),
    );
    return data;
  },

};


