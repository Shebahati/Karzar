/** Product types mirrored from app/schemas/product.py, extended for the storefront. */

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
  slug?: string | null;
  breadcrumb?: string[];
  ancestor_ids?: number[];
  hierarchy_label?: string | null;
};
export type BrandBrief = Pick<Brand, "id" | "name"> & {
  country?: string | null;
};

export interface ProductImage {
  id: number;
  url: string;
  is_primary: boolean;
}

/**
 * The structured `specifications` payload the storefront PDP renders.
 * Mirrors the JSONB shape the admin "Ultimate Product Entry Form" produces:
 * - technical_specs / dimensions: ordered arrays of key/value objects.
 * - features: a flat map of boolean flags plus optional dynamic detail keys.
 */
export interface SpecItem {
  key: string;
  value: string;
}

export interface ProductSpecifications {
  technical_specs: SpecItem[];
  dimensions: SpecItem[];
  features: Record<string, boolean | string>;
}

export interface ProductSummary {
  id: number;
  sku: string;
  name: string;
  thumbnail: string | null;
  base_price: string | null;
  stock_status: string;
  availability: boolean;
  is_original: boolean;
  category: CategoryBrief | null;
  brand: BrandBrief | null;
  /** Optional storefront marketing flags. */
  discount_percent?: number | null;
  original_price?: string | null;
}

export interface ProductDetail {
  id: number;
  sku: string;
  name: string;
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
  description: string | null;
  specifications: ProductSpecifications;
  created_at: string;
  updated_at: string;
}

export type ProductListResponse = PaginatedResponse<ProductSummary>;

export type ProductSort =
  | "newest"
  | "price_asc"
  | "price_desc"
  | "discount_desc"
  | "stock_first"
  | "name_asc"
  | "name_desc";

export interface ProductListParams {
  skip?: number;
  limit?: number;
  category_id?: number;
  /** Multi-brand filter (API: repeated `brand_id`). Single id still works. */
  brand_ids?: number[];
  search?: string;
  min_price?: number;
  max_price?: number;
  /** Multi-country filter (API: repeated `country`). */
  countries?: string[];
  in_stock?: boolean;
  sort?: ProductSort;
  /** spec_* filters encoded as dot-path keys (e.g. technical_specs.grade). */
  spec_filters?: Record<string, string>;
}
