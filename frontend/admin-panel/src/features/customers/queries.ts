"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { customersService } from "@/services/customers";
import type { ApiError } from "@/lib/api-client";
import type { CustomerListParams, CustomerUpdatePayload } from "@/types/customer";

export const customersKeys = {
  all: ["customers"] as const,
  list: (params: CustomerListParams) => [...customersKeys.all, "list", params] as const,
  detail: (id: number) => [...customersKeys.all, "detail", id] as const,
};

export function useCustomers(params: CustomerListParams = {}) {
  return useQuery({
    queryKey: customersKeys.list(params),
    queryFn: () => customersService.list(params),
    placeholderData: keepPreviousData,
  });
}

export function useCustomer(id: number, enabled = true) {
  return useQuery({
    queryKey: customersKeys.detail(id),
    queryFn: () => customersService.get(id),
    enabled: enabled && Number.isFinite(id),
  });
}

export function useUpdateCustomer(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CustomerUpdatePayload & { stepUpToken?: string }) =>
      customersService.update(id, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: customersKeys.all });
    },
  });
}

export function useDeleteCustomer() {
  const queryClient = useQueryClient();
  return useMutation<void, ApiError, { id: number; stepUpToken: string }>({
    mutationFn: ({ id, stepUpToken }) => customersService.delete(id, stepUpToken),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: customersKeys.all });
    },
  });
}
