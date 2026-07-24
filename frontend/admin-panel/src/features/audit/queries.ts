"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { auditService } from "@/services/audit";
import type { AuditLogListParams } from "@/types/audit";

export const auditKeys = {
  all: ["audit-logs"] as const,
  list: (params: AuditLogListParams) => [...auditKeys.all, "list", params] as const,
};

export function useAuditLogs(params: AuditLogListParams = {}) {
  return useQuery({
    queryKey: auditKeys.list(params),
    queryFn: () => auditService.list(params),
    placeholderData: keepPreviousData,
  });
}
