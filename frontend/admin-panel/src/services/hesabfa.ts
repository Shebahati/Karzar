import { apiClient } from "@/lib/api-client";

export interface HesabfaSalesSummary {
  website_paid_total_toman: string;
  website_paid_order_count: number;
  hesabfa_sales_total: string | null;
  hesabfa_sales_total_toman: string | null;
  hesabfa_invoice_count: number | null;
  hesabfa_currency_unit: string;
  hesabfa_available: boolean;
  hesabfa_error: string | null;
}

export interface HesabfaStatus {
  enabled: boolean;
  configured: boolean;
  test_mode: boolean;
  base_url: string;
  warehouse_code: number | null;
  currency_unit: string;
  stock_sync_interval_seconds: number;
}

export const hesabfaService = {
  async getStatus(): Promise<HesabfaStatus> {
    const { data } = await apiClient.get<HesabfaStatus>("/hesabfa/status");
    return data;
  },

  async getSalesSummary(): Promise<HesabfaSalesSummary> {
    const { data } = await apiClient.get<HesabfaSalesSummary>("/hesabfa/sales-summary");
    return data;
  },
};
