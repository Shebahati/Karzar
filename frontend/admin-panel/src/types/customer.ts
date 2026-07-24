/** Customer types for admin panel. */

import type { PaginatedResponse } from "./common";

export interface CustomerSummary {
  id: number;
  phone: string;
  full_name: string | null;
  is_active: boolean;
  order_count: number;
  created_at: string;
  category: string | null;
  tags: string[];
}

export interface CustomerDetail extends CustomerSummary {
  email: string | null;
  note: string | null;
}

export type CustomerListResponse = PaginatedResponse<CustomerSummary>;

export interface CustomerListParams {
  skip?: number;
  limit?: number;
  search?: string;
}

export interface CustomerUpdatePayload {
  full_name?: string | null;
  is_active?: boolean;
  note?: string | null;
  category?: string | null;
  tags?: string[];
}

export const CUSTOMER_CATEGORIES = [
  "خرده",
  "سازمانی",
  "VIP",
  "نمایندگی",
  "عمده",
] as const;
