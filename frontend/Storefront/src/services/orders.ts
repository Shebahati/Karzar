import { apiClient } from "@/lib/api-client";
import { getMockApi } from "@/lib/get-mock-api";
import { env } from "@/config/env";
import { buildOrderTimeline } from "@/lib/order-timeline";
import type {
  OrderListResponse,
  OrderTracking,
  OrderTrackingEvent,
  OrderStatus,
} from "@/types/order";
import { ORDER_STATUS_LABELS } from "@/lib/constants";

interface TrackingBackendResponse {
  tracking_code: string;
  status: OrderStatus;
  status_label: string;
  mode: "purchase" | "inquiry";
  created_at: string;
  items?: Array<{
    product_id: number;
    quantity: number;
    unit_price: string | null;
  }>;
  timeline?: Array<{
    status: string;
    status_label: string;
    occurred_at: string;
    description?: string | null;
    actor?: string | null;
  }>;
}

function annotateTimeline(
  events: OrderTrackingEvent[],
  currentStatus: OrderStatus,
): OrderTrackingEvent[] {
  return events.map((event, index) => ({
    ...event,
    is_complete: event.status !== currentStatus || index < events.length - 1,
    is_current: event.status === currentStatus,
  }));
}

export const orderService = {
  async listMine(params: { skip?: number; limit?: number } = {}): Promise<OrderListResponse> {
    if (env.USE_MOCK) return (await getMockApi()).listMyOrders(params);
    const { data } = await apiClient.get<OrderListResponse>("/orders/me", { params });
    return data;
  },

  async track(trackingCode: string): Promise<OrderTracking> {
    if (env.USE_MOCK) return (await getMockApi()).trackOrder(trackingCode);

    const { data } = await apiClient.get<TrackingBackendResponse>(
      `/orders/track/${trackingCode}`,
    );

    const serverTimeline = (data.timeline ?? []).map((event) => ({
      status: event.status as OrderStatus,
      status_label: event.status_label,
      occurred_at: event.occurred_at,
      description: event.description ?? null,
    }));

    const timelineEstimated = serverTimeline.length === 0;
    const timeline = timelineEstimated
      ? buildOrderTimeline({
          status: data.status,
          mode: data.mode,
          created_at: data.created_at,
        })
      : annotateTimeline(serverTimeline, data.status);

    return {
      tracking_code: data.tracking_code,
      status: data.status,
      status_label: data.status_label,
      mode: data.mode,
      created_at: data.created_at,
      // Public tracking intentionally omits PII / logistics fields.
      estimated_total: null,
      postal_tracking_code: null,
      delivery_eta: null,
      items: data.items ?? [],
      timeline,
      timeline_estimated: timelineEstimated,
    };
  },

  async getByTrackingCode(trackingCode: string): Promise<OrderTracking> {
    return this.track(trackingCode);
  },
};

export { ORDER_STATUS_LABELS };
