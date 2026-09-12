import { apiClient, withStepUp } from "@/lib/api-client";
import type { AdminShipment } from "@/features/orders/shipment-actions";

export const shippingAdminService = {
  async list(orderId: number): Promise<AdminShipment[]> {
    const { data } = await apiClient.get<AdminShipment[]>(`/orders/${orderId}/shipments`);
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
