import { apiClient, withStepUp } from "@/lib/api-client";
import { getMockApi } from "@/lib/get-mock-api";
import { env } from "@/config/env";
import type {
  CustomerDetail,
  CustomerListParams,
  CustomerListResponse,
  CustomerUpdatePayload,
} from "@/types/customer";

interface CustomerBackend {
  id: number;
  phone_number: string;
  full_name: string | null;
  is_active: boolean;
  email?: string | null;
  order_count?: number;
  created_at?: string;
  note?: string | null;
  category?: string | null;
  tags?: string[];
}

function mapCustomer(raw: CustomerBackend): CustomerDetail {
  return {
    id: raw.id,
    phone: raw.phone_number,
    full_name: raw.full_name,
    is_active: raw.is_active,
    email: raw.email ?? null,
    order_count: raw.order_count ?? 0,
    created_at: raw.created_at ?? new Date().toISOString(),
    note: raw.note ?? null,
    category: raw.category ?? null,
    tags: raw.tags ?? [],
  };
}

export const customersService = {
  async list(params: CustomerListParams = {}): Promise<CustomerListResponse> {
    if (env.USE_MOCK) return (await getMockApi()).listCustomers(params);
    const { data } = await apiClient.get<{ data: CustomerBackend[]; meta: CustomerListResponse["meta"] }>(
      "/users/",
      { params },
    );
    return {
      data: (data.data ?? []).map(mapCustomer),
      meta: data.meta,
    };
  },

  async get(id: number): Promise<CustomerDetail> {
    if (env.USE_MOCK) return (await getMockApi()).getCustomer(id);
    const { data } = await apiClient.get<CustomerBackend>(`/users/${id}`);
    return mapCustomer(data);
  },

  async update(
    id: number,
    payload: CustomerUpdatePayload & { stepUpToken?: string },
  ): Promise<CustomerDetail> {
    if (env.USE_MOCK) return (await getMockApi()).updateCustomer(id, payload);

    const { stepUpToken, ...body } = payload;
    const { data } = await apiClient.patch<CustomerBackend>(
      `/users/${id}`,
      body,
      stepUpToken ? withStepUp(stepUpToken) : undefined,
    );
    return mapCustomer(data);
  },

  async delete(id: number, stepUpToken: string): Promise<void> {
    if (env.USE_MOCK) return (await getMockApi()).deleteCustomer(id, stepUpToken);
    await apiClient.delete(`/users/${id}`, withStepUp(stepUpToken));
  },
};
