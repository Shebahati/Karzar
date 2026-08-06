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
  slug?: string | null;
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
  /**
   * Soft accessory labels / codes from catalog JSONB.
   * Often empty — PDP must still render an honest empty slot (FE-002 / Bible conflict matrix).
   * Evidence: docs/examples/sample_product.json, docs/FRONTEND_INTEGRATION.md.
   */
  optional_accessories?: string[];
}

export interface ProductSummary {
  id: number;
  sku: string;
  slug?: string | null;
  name: string;
  short_description?: string | null;
  thumbnail: string | null;
  /**
   * PLP hover swap: list API returns at most primary + one extra image.
   * Mock data may include a fuller gallery; ProductCard only needs two URLs.
   */
  images?: ProductImage[];
  base_price: string | null;
  stock_status: string;
  availability: boolean;
  is_original: boolean;
  category: CategoryBrief | null;
  brand: BrandBrief | null;
  /** Optional storefront marketing flags. */
  discount_percent?: number | null;
  original_price?: string | null;
  updated_at?: string;
}

export interface ProductDetail {
  id: number;
  sku: string;
  slug?: string | null;
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
  short_description?: string | null;
  description: string | null;
  meta_title?: string | null;
  meta_description?: string | null;
  /** Live API may omit/null this; PDP must null-guard. */
  specifications: ProductSpecifications | null;
  created_at: string;
  updated_at: string;
}

export type ProductListResponse = PaginatedResponse<ProductSummary>;

/**
 * Live `GET /api/v1/products/` `sort` values (OpenAPI / 422 details).
 * Do not invent keys — unsupported values return VALIDATION_FAILED.
 */
export const API_PRODUCT_SORTS = [
  "newest",
  "price_asc",
  "price_desc",
  "name_asc",
  "name_desc",
] as const;

export type ProductSort = (typeof API_PRODUCT_SORTS)[number];

export function isApiProductSort(value: string): value is ProductSort {
  return (API_PRODUCT_SORTS as readonly string[]).includes(value);
}

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
  /**
   * FE-only: products with an active discount (`discount_percent > 0` or
   * compare-at / original price above sale price). Not a live API query key —
   * mock filters natively; live responses are filtered client-side.
   */
  on_sale?: boolean;
  sort?: ProductSort;
  /** spec_* filters encoded as dot-path keys (e.g. technical_specs.grade). */
  spec_filters?: Record<string, string>;
}

/** True when the product carries a real discount signal for PLP / deal rails. */
export function productHasDiscount(p: {
  discount_percent?: number | null;
  original_price?: string | number | null;
  base_price?: string | number | null;
}): boolean {
  if ((p.discount_percent ?? 0) > 0) return true;
  if (p.original_price == null || p.base_price == null) return false;
  const original = Number(p.original_price);
  const base = Number(p.base_price);
  return Number.isFinite(original) && Number.isFinite(base) && original > base;
}
