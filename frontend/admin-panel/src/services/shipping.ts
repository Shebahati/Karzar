import { apiClient, withStepUp } from "@/lib/api-client";
import type { AdminShipment } from "@/features/orders/shipment-actions";

export interface PackedQuoteOption {
  carrier_code: string;
  service_code: string;
  service_name?: string | null;
  customer_amount_toman: string;
  provider_amount_toman: string;
  pickup_amount_toman?: string | null;
}

export interface PackedQuoteResult {
  shipment: AdminShipment;
  options: PackedQuoteOption[];
  order_estimated_total_unchanged?: string | null;
}

export const shippingAdminService = {
  async list(orderId: number): Promise<AdminShipment[]> {
    const { data } = await apiClient.get<AdminShipment[]>(`/orders/${orderId}/shipments`);
    return data;
  },

  async setFinalPackage(
    orderId: number,
    shipmentId: number,
    body: {
      length_cm: number;
      width_cm: number;
      height_cm: number;
      weight_grams: number;
      is_fragile: boolean;
      is_liquid: boolean;
    },
  ): Promise<AdminShipment> {
    const { data } = await apiClient.post<AdminShipment>(
      `/orders/${orderId}/shipments/${shipmentId}/final-package`,
      body,
    );
    return data;
  },

  async packedQuote(orderId: number, shipmentId: number): Promise<PackedQuoteResult> {
    const { data } = await apiClient.post<PackedQuoteResult>(
      `/orders/${orderId}/shipments/${shipmentId}/packed-quote`,
    );
    return data;
  },

  async selectService(
    orderId: number,
    shipmentId: number,
    body: { carrier_code: string; service_code: string },
  ): Promise<AdminShipment> {
    const { data } = await apiClient.post<AdminShipment>(
      `/orders/${orderId}/shipments/${shipmentId}/select-service`,
      body,
    );
    return data;
  },

  async scheduleBooking(orderId: number, shipmentId: number): Promise<AdminShipment> {
    const { data } = await apiClient.post<AdminShipment>(
      `/orders/${orderId}/shipments/${shipmentId}/schedule-booking`,
    );
    return data;
  },

  async book(orderId: number, shipmentId: number): Promise<AdminShipment> {
    const { data } = await apiClient.post<AdminShipment>(
      `/orders/${orderId}/shipments/${shipmentId}/book`,
    );
    return data;
  },

  async markReady(orderId: number, shipmentId: number): Promise<AdminShipment> {
    const { data } = await apiClient.post<AdminShipment>(
      `/orders/${orderId}/shipments/${shipmentId}/ready`,
    );
    return data;
  },

  async refreshTracking(orderId: number, shipmentId: number): Promise<AdminShipment> {
    const { data } = await apiClient.post<AdminShipment>(
      `/orders/${orderId}/shipments/${shipmentId}/refresh-tracking`,
    );
    return data;
  },

  async cancel(orderId: number, shipmentId: number, reason: string, stepUpToken: string): Promise<AdminShipment> {
    const { data } = await apiClient.post<AdminShipment>(
      `/orders/${orderId}/shipments/${shipmentId}/cancel`,
      { reason },
      withStepUp(stepUpToken),
    );
    return data;
  },

  async edit(
    orderId: number,
    shipmentId: number,
    body: {
      address_line?: string | null;
      postal_code?: string | null;
      first_name?: string | null;
      last_name?: string | null;
      mobile_no?: string | null;
    },
  ): Promise<AdminShipment> {
    const { data } = await apiClient.post<AdminShipment>(
      `/orders/${orderId}/shipments/${shipmentId}/edit`,
      body,
    );
    return data;
  },

  async downloadLabel(orderId: number, shipmentId: number): Promise<void> {
    const { data } = await apiClient.get<Blob>(
      `/orders/${orderId}/shipments/${shipmentId}/label`,
      { responseType: "blob" },
    );
    const url = URL.createObjectURL(data);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `karzar-label-${shipmentId}.pdf`;
    anchor.click();
    URL.revokeObjectURL(url);
  },
};
