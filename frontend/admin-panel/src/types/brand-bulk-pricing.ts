
export type BrandBulkAdjustmentMode = "percent" | "fixed";
export type BrandBulkAdjustmentDirection = "increase" | "decrease";

export interface BrandBulkPricingAdjustPayload {
  brand_id: number;
  mode: BrandBulkAdjustmentMode;
  direction: BrandBulkAdjustmentDirection;
  amount: string;
}

export interface BrandBulkPricingPreviewLine {
  product_id: number;
  sku: string;
  old_base_price: string | null;
  new_base_price: string | null;
  original_price: string | null;
  line_status: string;
  conflict_reason?: string | null;
}

export interface BrandBulkPricingPreview {
  brand_id: number;
  mode: BrandBulkAdjustmentMode;
  direction: BrandBulkAdjustmentDirection;
  amount: string;
  manifest_sha256: string;
  catalog_fingerprint_sha256: string;
  total_products: number;
  eligible_count: number;
  conflict_count: number;
  skipped_count: number;
  lines: BrandBulkPricingPreviewLine[];
}

export interface BrandBulkPricingOperationSummary {
  id: number;
  brand_id: number;
  status: string;
  mode: BrandBulkAdjustmentMode;
  direction: BrandBulkAdjustmentDirection;
  amount: string;
  manifest_sha256: string;
  catalog_fingerprint_sha256: string;
  actor_user_id: number | null;
  confirmed_at: string;
  applied_at?: string | null;
  eligible_count: number;
  conflict_count: number;
}

export interface BrandBulkPricingOperationDetail extends BrandBulkPricingOperationSummary {
  lines: BrandBulkPricingPreviewLine[];
  apply_error?: string | null;
}

export interface BrandBulkPricingApplyResult {
  operation_id: number;
  status: string;
  applied_count: number;
  skipped_count: number;
  conflict_count: number;
  drift_detected: boolean;
}
