import { apiClient } from "@/lib/api-client";

/** Website paid totals only — Hesabfa fields are always null/disabled. */
export interface WebsitePaidSales {
  website_paid_total_toman: string;
  website_paid_order_count: number;
}

export interface HesabfaStatus {
  enabled: boolean;
  configured: boolean;
  test_mode: boolean;
  base_url: string;
  warehouse_code: number | null;
  currency_unit: string;
  stock_sync_interval_seconds: number;
  stock_pull_enabled?: boolean;
  item_push_enabled?: boolean;
  admin_reads_enabled?: boolean;
}

export const hesabfaService = {
  async getStatus(): Promise<HesabfaStatus> {
    const { data } = await apiClient.get<HesabfaStatus>("/hesabfa/status");
    return data;
  },

  async getWebsitePaidSales(): Promise<WebsitePaidSales> {
    const { data } = await apiClient.get<{
      website_paid_total_toman: string;
      website_paid_order_count: number;
    }>("/hesabfa/sales-summary");
    return {
      website_paid_total_toman: data.website_paid_total_toman,
      website_paid_order_count: data.website_paid_order_count,
    };
  },
};
