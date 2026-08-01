/**
 * Knowledge Graph data-access facade (KB-001 read APIs).
 * Read-only admin views — no Facts / dual-write / CLASSIFIED_AS.
 */

import { apiClient } from "@/lib/api-client";
import { getMockApi } from "@/lib/get-mock-api";
import { env } from "@/config/env";
import type {
  KnowledgeEdgeListParams,
  KnowledgeEdgeListResponse,
  ProductNeighborhood,
} from "@/types/knowledge";

export const knowledgeService = {
  async listEdges(params: KnowledgeEdgeListParams = {}): Promise<KnowledgeEdgeListResponse> {
    if (env.USE_MOCK) return (await getMockApi()).listKnowledgeEdges(params);
    const { data } = await apiClient.get<KnowledgeEdgeListResponse>("/knowledge/edges", {
      params,
    });
    return data;
  },

  async getProductNeighborhood(productId: number): Promise<ProductNeighborhood> {
    if (env.USE_MOCK) return (await getMockApi()).getProductNeighborhood(productId);
    const { data } = await apiClient.get<ProductNeighborhood>(
      `/knowledge/products/${productId}/neighborhood`,
    );
    return data;
  },
};
