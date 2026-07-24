import axios, {
  AxiosError,
  type AxiosInstance,
  type InternalAxiosRequestConfig,
} from "axios";

import { env } from "@/config/env";
import type { ApiErrorPayload, ErrorCode } from "@/types/common";

/**
 * Normalized error thrown by every data call (mock or live).
 *
 * UI layers can branch on `code` (e.g. STEP_UP_REQUIRED) and surface
 * `fieldErrors` directly onto react-hook-form fields.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly code: ErrorCode | string;
  readonly fieldErrors: Record<string, string>;
  readonly retryAfterSeconds: number | null;

  constructor(params: {
    status: number;
    code: ErrorCode | string;
    message: string;
    fieldErrors?: Record<string, string>;
    retryAfterSeconds?: number | null;
  }) {
    super(params.message);
    this.name = "ApiError";
    this.status = params.status;
    this.code = params.code;
    this.fieldErrors = params.fieldErrors ?? {};
    this.retryAfterSeconds = params.retryAfterSeconds ?? null;
  }
}

const STEP_UP_HEADER = "X-Step-Up-Token";
const ACCESS_TOKEN_STORAGE_KEY = "karzar.access_token";
const REFRESH_TOKEN_STORAGE_KEY = "karzar.refresh_token";
const TOKEN_EXPIRES_AT_KEY = "karzar.access_token.expires_at";

let memoryAccessToken: string | null = null;
let memoryRefreshToken: string | null = null;
let memoryExpiresAt: number | null = null;
let refreshPromise: Promise<boolean> | null = null;
let purgedLegacyTokens = false;

function purgeLegacyLocalTokens(): void {
  if (typeof window === "undefined" || purgedLegacyTokens || env.USE_MOCK) return;
  purgedLegacyTokens = true;
  window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);
  window.localStorage.removeItem(TOKEN_EXPIRES_AT_KEY);
}

function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  purgeLegacyLocalTokens();
  if (env.USE_MOCK) {
    return window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
  }
  if (tokenStorage.isExpired()) return null;
  return memoryAccessToken;
}

function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  if (env.USE_MOCK) {
    return window.localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY);
  }
  return memoryRefreshToken;
}

function parseRetryAfter(header: string | undefined | null): number | null {
  if (!header) return null;
  const asInt = Number(header);
  if (!Number.isNaN(asInt) && asInt > 0) return asInt;
  const dateMs = Date.parse(header);
  if (!Number.isNaN(dateMs)) {
    return Math.max(1, Math.ceil((dateMs - Date.now()) / 1000));
  }
  return null;
}

export const apiClient: AxiosInstance = axios.create({
  baseURL: env.API_BASE_URL,
  timeout: 20_000,
  headers: { "Content-Type": "application/json" },
  withCredentials: !env.USE_MOCK,
});

export async function tryRefreshAccessToken(): Promise<boolean> {
  if (env.USE_MOCK) return false;
  const refresh = getRefreshToken();
  try {
    const { data } = await axios.post<{
      access_token: string;
      refresh_token: string;
      expires_in: number;
    }>(
      `${env.API_BASE_URL}/auth/refresh`,
      refresh ? { refresh_token: refresh } : {},
      {
        headers: { "Content-Type": "application/json" },
        timeout: 15_000,
        withCredentials: true,
      },
    );
    tokenStorage.set(data.access_token, data.expires_in, data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

async function ensureFreshAccessToken(): Promise<void> {
  if (env.USE_MOCK) return;
  if (!tokenStorage.isNearExpiry() && memoryAccessToken) return;
  if (!refreshPromise) {
    refreshPromise = tryRefreshAccessToken().finally(() => {
      refreshPromise = null;
    });
  }
  await refreshPromise;
}

apiClient.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  if (!env.USE_MOCK && typeof window !== "undefined") {
    await ensureFreshAccessToken();
  }
  const token = getAccessToken();
  if (token) {
    config.headers.set("Authorization", `Bearer ${token}`);
  }
  return config;
});

function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;

  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ detail?: ApiErrorPayload } & Partial<ApiErrorPayload>>;
    const status = axiosError.response?.status ?? 0;
    const body = axiosError.response?.data;
    const retryAfter = parseRetryAfter(
      axiosError.response?.headers?.["retry-after"] as string | undefined,
    );

    const payload: ApiErrorPayload | undefined =
      (body?.detail as ApiErrorPayload | undefined) ??
      (body && "error_code" in body ? (body as ApiErrorPayload) : undefined);

    if (payload) {
      const fieldErrors: Record<string, string> = {};
      for (const detail of payload.details ?? []) {
        if (detail.field) fieldErrors[detail.field] = detail.message;
      }
      return new ApiError({
        status,
        code: payload.error_code,
        message: payload.message,
        fieldErrors,
        retryAfterSeconds: retryAfter,
      });
    }

    return new ApiError({
      status,
      code: status === 0 ? "INTERNAL_ERROR" : status === 429 ? "RATE_LIMITED" : "BAD_REQUEST",
      message:
        status === 0
          ? "ارتباط با سرور برقرار نشد. اتصال شبکه را بررسی کنید."
          : status === 429
            ? "تعداد درخواست‌ها زیاد است. کمی بعد دوباره تلاش کنید."
            : "خطایی در پردازش درخواست رخ داد.",
      retryAfterSeconds: retryAfter,
    });
  }

  return new ApiError({
    status: 0,
    code: "INTERNAL_ERROR",
    message: "خطای ناشناخته‌ای رخ داد.",
  });
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
      if (original && !original._retry) {
        original._retry = true;
        const refreshed = await tryRefreshAccessToken();
        if (refreshed) {
          original.headers = original.headers ?? {};
          const next = getAccessToken();
          if (next) original.headers.Authorization = `Bearer ${next}`;
          return apiClient.request(original);
        }
      }
      tokenStorage.clear();
      if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
        const next = encodeURIComponent(window.location.pathname);
        window.location.href = `/login?next=${next}&expired=1`;
      }
    }
    return Promise.reject(toApiError(error));
  },
);

export function withStepUp<T extends Record<string, unknown>>(
  stepUpToken: string,
  config?: T,
): T & { headers: Record<string, string> } {
  return {
    ...(config ?? ({} as T)),
    headers: {
      ...((config as { headers?: Record<string, string> })?.headers ?? {}),
      [STEP_UP_HEADER]: stepUpToken,
    },
  };
}

export const tokenStorage = {
  set(token: string, expiresInSeconds?: number, refreshToken?: string | null) {
    if (typeof window === "undefined") return;
    if (env.USE_MOCK) {
      window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token);
      if (expiresInSeconds != null) {
        const expiresAt = Date.now() + expiresInSeconds * 1000;
        window.localStorage.setItem(TOKEN_EXPIRES_AT_KEY, String(expiresAt));
      }
      if (refreshToken) {
        window.localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, refreshToken);
      }
      return;
    }
    purgeLegacyLocalTokens();
    memoryAccessToken = token;
    if (expiresInSeconds != null) {
      memoryExpiresAt = Date.now() + expiresInSeconds * 1000;
    }
    if (refreshToken) {
      memoryRefreshToken = refreshToken;
    }
  },
  getExpiresAt(): number | null {
    if (typeof window === "undefined") return null;
    if (env.USE_MOCK) {
      const raw = window.localStorage.getItem(TOKEN_EXPIRES_AT_KEY);
      return raw ? Number(raw) : null;
    }
    return memoryExpiresAt;
  },
  isExpired(): boolean {
    const expiresAt = this.getExpiresAt();
    if (!expiresAt) return false;
    return Date.now() >= expiresAt;
  },
  isNearExpiry(skewMs = 60_000): boolean {
    const expiresAt = this.getExpiresAt();
    if (!expiresAt) return false;
    return Date.now() >= expiresAt - skewMs;
  },
  clear() {
    if (typeof window === "undefined") return;
    memoryAccessToken = null;
    memoryRefreshToken = null;
    memoryExpiresAt = null;
    window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
    window.localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);
    window.localStorage.removeItem(TOKEN_EXPIRES_AT_KEY);
  },
  /** Current access token (memory or mock LS) for edge-session bootstrap. */
  getAccessToken(): string | null {
    return getAccessToken();
  },
};

export function createIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `idem-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}
