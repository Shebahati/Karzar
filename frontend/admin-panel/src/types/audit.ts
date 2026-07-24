/** Admin audit log types — GET /users/audit-logs/list. */

import type { PaginatedResponse } from "./common";

export interface AuditLogEntry {
  id: number;
  actor_user_id: number | null;
  action: string;
  entity_type: string;
  entity_id: string;
  details: Record<string, unknown> | null;
  created_at: string;
}

export type AuditLogListResponse = PaginatedResponse<AuditLogEntry>;

export interface AuditLogListParams {
  skip?: number;
  limit?: number;
  entity_type?: string;
  entity_id?: string;
}
