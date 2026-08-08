"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { issuedProformasService } from "@/services/issued-proformas";
import type { IssuedProformaCreateInput } from "@/types/invoice-doc";

export const issuedProformaKeys = {
  all: ["issued-proformas"] as const,
  list: () => [...issuedProformaKeys.all, "list"] as const,
};

export function useIssuedProformas() {
  return useQuery({
    queryKey: issuedProformaKeys.list(),
    queryFn: () => issuedProformasService.list(),
    staleTime: 0,
  });
}

export function useCreateIssuedProforma() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: IssuedProformaCreateInput) =>
      issuedProformasService.create(input),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: issuedProformaKeys.all });
    },
  });
}

export function useRemoveIssuedProforma() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => issuedProformasService.remove(id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: issuedProformaKeys.all });
    },
  });
}
