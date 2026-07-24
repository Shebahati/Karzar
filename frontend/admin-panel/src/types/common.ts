/** Shared API envelope types mirrored from the FastAPI backend. */

export interface PaginationMeta {
  total_count: number;
  skip: number;
  limit: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface PaginatedResponse<T> {
  data: T[];
  meta: PaginationMeta;
}

/** Canonical error contract: { error_code, message, details[] }. */
export interface ErrorDetail {
  field?: string | null;
  message: string;
}

export interface ApiErrorPayload {
  error_code: string;
  message: string;
  details: ErrorDetail[];
}

export type ErrorCode =
  | "BAD_REQUEST"
  | "UNAUTHORIZED"
  | "FORBIDDEN"
  | "NOT_FOUND"
  | "CONFLICT"
  | "VALIDATION_FAILED"
  | "STEP_UP_REQUIRED"
  | "STEP_UP_INVALID"
  | "STEP_UP_MISMATCH"
  | "STEP_UP_NOT_CONFIGURED"
  | "RATE_LIMITED"
  | "INTERNAL_ERROR";
