"use client";

import { useQuery } from "@tanstack/react-query";

import { knowledgeService } from "@/services/knowledge";
import type { KnowledgeEdgeListParams } from "@/types/knowledge";

export const knowledgeKeys = {
  all: ["knowledge"] as const,
  edges: (params: KnowledgeEdgeListParams) => [...knowledgeKeys.all, "edges", params] as const,
  neighborhood: (productId: number) =>
    [...knowledgeKeys.all, "neighborhood", productId] as const,
};

export function useKnowledgeEdges(params: KnowledgeEdgeListParams = {}, enabled = true) {
  return useQuery({
    queryKey: knowledgeKeys.edges(params),
    queryFn: () => knowledgeService.listEdges(params),
    enabled,
    staleTime: 30 * 1000,
  });
}

export function useProductNeighborhood(productId: number, enabled = true) {
  return useQuery({
    queryKey: knowledgeKeys.neighborhood(productId),
    queryFn: () => knowledgeService.getProductNeighborhood(productId),
    enabled: enabled && Number.isFinite(productId) && productId > 0,
    staleTime: 30 * 1000,
  });
}
