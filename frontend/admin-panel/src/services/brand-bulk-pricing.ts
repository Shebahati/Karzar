
import { apiClient, withStepUp } from "@/lib/api-client";
import type {
  BrandBulkPricingAdjustPayload,
  BrandBulkPricingApplyResult,
  BrandBulkPricingOperationDetail,
  BrandBulkPricingOperationSummary,
  BrandBulkPricingPreview,
} from "@/types/brand-bulk-pricing";

const BASE = "/admin/brand-bulk-pricing";

export const brandBulkPricingService = {
  async preview(payload: BrandBulkPricingAdjustPayload): Promise<BrandBulkPricingPreview> {
    const { data } = await apiClient.post<BrandBulkPricingPreview>(`${BASE}/preview`, payload);
    return data;
  },

  async confirm(
    payload: BrandBulkPricingAdjustPayload & { manifest_sha256: string },
  ): Promise<BrandBulkPricingOperationDetail> {
    const { data } = await apiClient.post<BrandBulkPricingOperationDetail>(`${BASE}/confirm`, payload);
    return data;
  },

  async apply(
    operationId: number,
    stepUpToken: string,
    idempotencyKey: string,
  ): Promise<BrandBulkPricingApplyResult> {
    const { data } = await apiClient.post<BrandBulkPricingApplyResult>(
      `${BASE}/operations/${operationId}/apply`,
      {},
      withStepUp(stepUpToken, { headers: { "Idempotency-Key": idempotencyKey } }),
    );
    return data;
  },

  async listOperations(params?: { brand_id?: number; skip?: number; limit?: number }) {
    const { data } = await apiClient.get<{ data: BrandBulkPricingOperationSummary[]; total: number }>(
      `${BASE}/operations`,
      { params },
    );
    return data;
  },

  async getOperation(operationId: number): Promise<BrandBulkPricingOperationDetail> {
    const { data } = await apiClient.get<BrandBulkPricingOperationDetail>(
      `${BASE}/operations/${operationId}`,
    );
    return data;
  },
};
