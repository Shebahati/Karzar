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

export interface ErrorDetail {
  field?: string | null;
  message: string;
}

export interface ApiErrorPayload {
  error_code: string;
  message: string;
  details: ErrorDetail[];
}
