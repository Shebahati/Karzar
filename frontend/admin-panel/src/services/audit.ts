import { apiClient } from "@/lib/api-client";
import { getMockApi } from "@/lib/get-mock-api";
import { env } from "@/config/env";
import type { AuditLogListParams, AuditLogListResponse } from "@/types/audit";

/**
 * Admin audit-log facade — GET /users/audit-logs/list.
 * Backend only supports `entity_type` / `entity_id` filters (no action/actor/date-range yet).
 */
export const auditService = {
  async list(params: AuditLogListParams = {}): Promise<AuditLogListResponse> {
    if (env.USE_MOCK) return (await getMockApi()).listAuditLogs(params);
    const { data } = await apiClient.get<AuditLogListResponse>("/users/audit-logs/list", {
      params,
    });
    return data;
  },
};
