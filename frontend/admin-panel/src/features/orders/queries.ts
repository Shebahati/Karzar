"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ordersService } from "@/services/orders";
import type { ApiError } from "@/lib/api-client";
import type { OrderListParams, OrderStatusUpdatePayload, IssueQuotePayload } from "@/types/order";

export const ordersKeys = {
  all: ["orders"] as const,
  list: (params: OrderListParams) => [...ordersKeys.all, "list", params] as const,
  detail: (id: number) => [...ordersKeys.all, "detail", id] as const,
};

export function useOrders(params: OrderListParams = {}) {
  return useQuery({
    queryKey: ordersKeys.list(params),
    queryFn: () => ordersService.list(params),
    placeholderData: keepPreviousData,
  });
}

export function useOrder(id: number, enabled = true) {
  return useQuery({
    queryKey: ordersKeys.detail(id),
    queryFn: () => ordersService.get(id),
    enabled: enabled && Number.isFinite(id),
  });
}

export function useUpdateOrderStatus(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: OrderStatusUpdatePayload & { stepUpToken?: string }) =>
      ordersService.updateStatus(id, payload, payload.stepUpToken),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ordersKeys.all });
    },
  });
}

export function useIssueQuote(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: IssueQuotePayload) => ordersService.issueQuote(id, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ordersKeys.all });
    },
  });
}

export function useArchiveOrder() {
  const queryClient = useQueryClient();
  return useMutation<void, ApiError, { id: number; stepUpToken: string }>({
    mutationFn: ({ id, stepUpToken }) => ordersService.archive(id, stepUpToken),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ordersKeys.all });
    },
  });
}
