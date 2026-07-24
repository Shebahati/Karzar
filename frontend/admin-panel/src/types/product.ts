/** Product types mirrored from app/schemas/product.py and app/db/models/product.py. */

import type { Brand, Category } from "./category";
import type { PaginatedResponse } from "./common";

export const STOCK_UNITS = ["piece", "kg", "meter", "pack"] as const;
export type StockUnit = (typeof STOCK_UNITS)[number];

export const STOCK_UNIT_LABELS: Record<StockUnit, string> = {
  piece: "عدد",
  kg: "کیلوگرم",
  meter: "متر",
  pack: "بسته",
};

export type CategoryBrief = Pick<Category, "id" | "name"> & {
  breadcrumb?: string[];
  hierarchy_label?: string | null;
};
export type BrandBrief = Pick<Brand, "id" | "name" | "country">;

/** Exact specifications dictionary shape for admin (C7). */
export interface ProductSpecificationsDict {
  technical_specs?: { key: string; value: string }[];
  features?: Record<string, boolean | string | string[] | number>;
  dimensions?: { key: string; value: number }[];
}

export type Specifications = ProductSpecificationsDict;

export interface ProductImage {
  id: number;
  url: string;
  is_primary: boolean;
}

export interface ProductSummary {
  id: number;
  sku: string;
  name: string;
  thumbnail: string | null;
  base_price: string | null;
  original_price: string | null;
  discount_percent: number | null;
  stock_status: string;
  availability: boolean;
  is_original: boolean;
  category: CategoryBrief | null;
  brand: BrandBrief | null;
}

export interface ProductDetail {
  id: number;
  sku: string;
  name: string;
  description: string | null;
  category_id: number | null;
  brand_id: number | null;
  category: CategoryBrief | null;
  brand: BrandBrief | null;
  base_price: string | null;
  original_price: string | null;
  discount_percent: number | null;
  stock_quantity: string;
  stock_unit: StockUnit;
  stock_status: string;
  low_stock: boolean;
  availability: boolean;
  warranty_text: string | null;
  weight_grams: string | null;
  is_original: boolean;
  tax_percent: string;
  is_active: boolean;
  pdf_catalog_url: string | null;
  thumbnail: string | null;
  images: ProductImage[];
  specifications: Specifications;
  created_at: string;
  updated_at: string;
}

/** Payload for POST /products — matches ProductCreate. */
export interface ProductCreatePayload {
  sku: string;
  name: string;
  description?: string | null;
  category_id: number;
  brand_id?: number | null;
  base_price?: number | null;
  original_price?: number | null;
  stock_quantity: number;
  stock_unit: StockUnit;
  warranty_text?: string | null;
  weight_grams?: number | null;
  is_original: boolean;
  tax_percent: number;
  is_active: boolean;
  pdf_catalog_url?: string | null;
  specifications: Specifications;
}

/** Payload for PUT /products/{id} — matches ProductUpdate (no stock_quantity). */
export interface ProductUpdatePayload {
  sku?: string;
  name?: string;
  description?: string | null;
  category_id?: number;
  brand_id?: number | null;
  base_price?: number | null;
  original_price?: number | null;
  stock_unit?: StockUnit;
  warranty_text?: string | null;
  weight_grams?: number | null;
  is_original?: boolean;
  tax_percent?: number;
  is_active?: boolean;
  pdf_catalog_url?: string | null;
  specifications?: Specifications;
}

export type ProductListResponse = PaginatedResponse<ProductSummary>;

export interface ProductListParams {
  skip?: number;
  limit?: number;
  category_id?: number;
  brand_id?: number;
  is_active?: boolean;
  is_deleted?: boolean;
  search?: string;
  min_price?: number;
  max_price?: number;
}

export interface ProductStockInfo {
  product_id: number;
  sku?: string;
  /** Backend StockStatusResponse field. */
  stock_quantity: string;
  stock_status: string;
  /** Convenience aliases used by older UI. */
  quantity?: string;
  unit?: StockUnit;
  low_stock?: boolean;
  availability?: boolean;
}

export interface ProductStockAdjustPayload {
  delta: number;
  reason?: string | null;
}

export interface ProductImageUploadResponse {
  id: number;
  url: string;
  is_primary: boolean;
}

/** Mirrors `ProductStatisticsResponse` — GET /products/statistics (super-admin only). */
export interface ProductStatisticsResponse {
  total_products: number;
  active_products: number;
  /** Sum of base_price * stock_quantity across all non-deleted products. */
  total_stock_value: string;
  total_stock_quantity: string;
  categories: number;
  brands: number;
}

/** Mirrors `ProductChangeLogEntry` — GET /products/{id}/change-log. */
export interface ProductChangeLogEntry {
  id: number;
  product_id: number;
  field_name: string;
  old_value: string | null;
  new_value: string | null;
  reason: string | null;
  created_at: string;
}

export type ProductChangeLogListResponse = PaginatedResponse<ProductChangeLogEntry>;

/** Mirrors `BulkStockAdjustItem` / `BulkStockAdjustRequest` — POST /products/bulk/stock-adjust. */
export interface BulkStockAdjustItem {
  product_id: number;
  quantity_delta: number;
  reason?: string | null;
}

export interface BulkStockAdjustResponse {
  updated_product_ids: number[];
}
