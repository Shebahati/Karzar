import { apiClient, withStepUp } from "@/lib/api-client";
import { getMockApi } from "@/lib/get-mock-api";
import { env } from "@/config/env";
import { formatShippingAddress } from "@/lib/shipping";
import type {
  OrderDetail,
  OrderDetailBackend,
  OrderLineItem,
  OrderListParams,
  OrderListResponse,
  IssueQuotePayload,
  OrderStatusUpdatePayload,
} from "@/types/order";

function mapLineItem(
  raw: OrderDetailBackend["items"][number],
  product?: { name: string; sku: string },
): OrderLineItem {
  const unit = raw.unit_price;
  const qty = raw.quantity;
  const lineTotal =
    unit != null ? String(Number(unit) * qty) : null;
  return {
    ...raw,
    product_name: product?.name ?? `محصول #${raw.product_id}`,
    sku: product?.sku ?? null,
    line_total: lineTotal,
  };
}

export function mapOrderDetail(
  raw: OrderDetailBackend,
  productsById?: Map<number, { name: string; sku: string }>,
): OrderDetail {
  return {
    id: raw.id,
    tracking_code: raw.tracking_code,
    status: raw.status,
    status_label: raw.status_label,
    mode: raw.mode,
    customer_name: raw.customer_full_name,
    customer_phone: raw.customer_phone,
    estimated_total: raw.estimated_total,
    created_at: raw.created_at,
    note: raw.note,
    shipping_address: formatShippingAddress(raw.shipping),
    payment_status: raw.payment_status,
    postal_tracking_code: raw.postal_tracking_code ?? null,
    delivery_eta: raw.delivery_eta ?? null,
    invoice: raw.invoice ?? null,
    timeline: raw.timeline ?? [],
    items: raw.items.map((item) =>
      mapLineItem(item, productsById?.get(item.product_id)),
    ),
  };
}

export const ordersService = {
  async list(params: OrderListParams = {}): Promise<OrderListResponse> {
    if (env.USE_MOCK) return (await getMockApi()).listOrders(params);
    const { data } = await apiClient.get<{
      data: Array<Omit<OrderDetailBackend, "items"> & { customer_name?: string }>;
      meta: OrderListResponse["meta"];
    }>("/orders/", { params });

    return {
      data: data.data.map((row) => ({
        id: row.id,
        tracking_code: row.tracking_code,
        status: row.status,
        status_label: row.status_label,
        mode: row.mode,
        customer_name: row.customer_full_name ?? row.customer_name ?? "",
        customer_phone: row.customer_phone,
        estimated_total: row.estimated_total,
        created_at: row.created_at,
      })),
      meta: data.meta,
    };
  },

  async get(id: number): Promise<OrderDetail> {
    if (env.USE_MOCK) return (await getMockApi()).getOrder(id);
    const { data } = await apiClient.get<OrderDetailBackend>(`/orders/${id}`);
    return mapOrderDetail(data);
  },

  async updateStatus(
    id: number,
    payload: OrderStatusUpdatePayload,
    stepUpToken?: string,
  ): Promise<OrderDetail> {
    if (env.USE_MOCK) return (await getMockApi()).updateOrderStatus(id, payload);

    const needsStepUp = payload.status === "cancelled";
    const { data } = await apiClient.patch<OrderDetailBackend>(
      `/orders/${id}/status`,
      {
        status: payload.status,
        note: payload.note ?? undefined,
        postal_tracking_code: payload.postal_tracking_code ?? undefined,
        delivery_eta: payload.delivery_eta ?? undefined,
      },
      needsStepUp && stepUpToken ? withStepUp(stepUpToken) : undefined,
    );
    return mapOrderDetail(data);
  },

  async issueQuote(id: number, payload: IssueQuotePayload): Promise<OrderDetail> {
    if (env.USE_MOCK) return (await getMockApi()).issueQuote(id, payload);
    const { data } = await apiClient.post<OrderDetailBackend>(`/orders/${id}/quote`, payload);
    return mapOrderDetail(data);
  },

  async archive(id: number, stepUpToken: string): Promise<void> {
    if (env.USE_MOCK) return (await getMockApi()).archiveOrder(id, stepUpToken);
    await apiClient.delete(`/orders/${id}`, withStepUp(stepUpToken));
  },
};
