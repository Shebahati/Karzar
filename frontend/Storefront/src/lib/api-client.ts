import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { env } from "@/config/env";
import type { ApiErrorPayload } from "@/types/common";

/**
 * Live mode uses HttpOnly cookies from the API (`withCredentials`).
 * Access/refresh JWTs are never written to localStorage in live mode.
 * Mock mode still uses localStorage tokens for offline demos.
 */
export const apiClient = axios.create({
  baseURL: env.API_BASE_URL,
  timeout: 15_000,
  headers: { "Content-Type": "application/json" },
  withCredentials: !env.USE_MOCK,
});

const TOKEN_KEY = "karzar.storefront.token";
const REFRESH_TOKEN_KEY = "karzar.storefront.refresh_token";
const TOKEN_EXPIRES_AT_KEY = "karzar.storefront.token.expires_at";
const CART_TOKEN_KEY = "karzar.storefront.cart_token";
/** Soft UX marker only — not a security boundary (real auth is HttpOnly API cookies). */
export const STOREFRONT_SESSION_COOKIE = "karzar_sf_session";

let memoryAccessToken: string | null = null;
let memoryRefreshToken: string | null = null;
let memoryExpiresAt: number | null = null;
let refreshPromise: Promise<boolean> | null = null;
let purgedLegacyTokens = false;

function purgeLegacyLocalTokens(): void {
  if (typeof window === "undefined" || purgedLegacyTokens || env.USE_MOCK) return;
  purgedLegacyTokens = true;
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  window.localStorage.removeItem(TOKEN_EXPIRES_AT_KEY);
}

export function setStorefrontSessionCookie(): void {
  if (typeof document === "undefined") return;
  document.cookie = `${STOREFRONT_SESSION_COOKIE}=1; Path=/; SameSite=Lax; Max-Age=${60 * 60 * 24 * 7}`;
}

export function clearStorefrontSessionCookie(): void {
  if (typeof document === "undefined") return;
  document.cookie = `${STOREFRONT_SESSION_COOKIE}=; Path=/; Max-Age=0; SameSite=Lax`;
}

export function hasStorefrontSessionCookie(): boolean {
  if (typeof document === "undefined") return false;
  return document.cookie.split(";").some((c) => c.trim().startsWith(`${STOREFRONT_SESSION_COOKIE}=`));
}

/** UI/auth gate: memory token, soft session marker, or mock LS token. */
export function isLoggedIn(): boolean {
  if (typeof window === "undefined") return false;
  if (env.USE_MOCK) {
    return Boolean(getStoredToken());
  }
  return Boolean(memoryAccessToken) || hasStorefrontSessionCookie();
}

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  purgeLegacyLocalTokens();
  if (env.USE_MOCK) {
    if (tokenStorage.isExpired()) return null;
    return window.localStorage.getItem(TOKEN_KEY);
  }
  if (tokenStorage.isExpired()) return null;
  return memoryAccessToken;
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  if (env.USE_MOCK) {
    return window.localStorage.getItem(REFRESH_TOKEN_KEY);
  }
  return memoryRefreshToken;
}

export function setStoredToken(
  token: string | null,
  expiresInSeconds?: number,
  refreshToken?: string | null,
): void {
  if (typeof window === "undefined") return;
  if (!token) {
    tokenStorage.clear();
    return;
  }

  if (env.USE_MOCK) {
    window.localStorage.setItem(TOKEN_KEY, token);
    if (expiresInSeconds != null) {
      window.localStorage.setItem(
        TOKEN_EXPIRES_AT_KEY,
        String(Date.now() + expiresInSeconds * 1000),
      );
    }
    if (refreshToken) {
      window.localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    }
    setStorefrontSessionCookie();
    return;
  }

  // Live: memory-only dual Bearer support; HttpOnly cookies are the source of truth.
  purgeLegacyLocalTokens();
  memoryAccessToken = token;
  if (expiresInSeconds != null) {
    memoryExpiresAt = Date.now() + expiresInSeconds * 1000;
  }
  if (refreshToken) {
    memoryRefreshToken = refreshToken;
  }
  setStorefrontSessionCookie();
}

/** Guest cart identity (≥32 chars) for X-Cart-Token. */
export function getOrCreateCartToken(): string {
  if (typeof window === "undefined") return "";
  let token = window.localStorage.getItem(CART_TOKEN_KEY);
  if (!token || token.length < 32) {
    token =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? `${crypto.randomUUID()}${crypto.randomUUID()}`.replace(/-/g, "")
        : `guest${Date.now()}${Math.random().toString(36).slice(2)}${Math.random().toString(36).slice(2)}`;
    window.localStorage.setItem(CART_TOKEN_KEY, token);
  }
  return token;
}

export function getCartToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(CART_TOKEN_KEY);
}

export function clearCartToken(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(CART_TOKEN_KEY);
}

export const tokenStorage = {
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
  /** True when access token expires within the next 60 seconds. */
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
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(REFRESH_TOKEN_KEY);
    window.localStorage.removeItem(TOKEN_EXPIRES_AT_KEY);
    window.localStorage.removeItem("karzar.storefront.customer");
    clearStorefrontSessionCookie();
  },
};

async function tryRefreshAccessToken(): Promise<boolean> {
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
    setStoredToken(data.access_token, data.expires_in, data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

export async function ensureFreshAccessToken(): Promise<boolean> {
  if (env.USE_MOCK) return Boolean(getStoredToken());
  // Prefer cookie session; refresh when near expiry or when soft marker exists without memory token.
  const needsRefresh =
    tokenStorage.isNearExpiry() ||
    (!memoryAccessToken && hasStorefrontSessionCookie());
  if (!needsRefresh && memoryAccessToken) return true;
  if (!needsRefresh && !hasStorefrontSessionCookie()) return false;
  if (!refreshPromise) {
    refreshPromise = tryRefreshAccessToken().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

apiClient.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  if (!env.USE_MOCK && typeof window !== "undefined") {
    await ensureFreshAccessToken();
  }
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  const cartToken = getCartToken();
  if (cartToken && !config.headers["X-Cart-Token"]) {
    config.headers["X-Cart-Token"] = cartToken;
  }
  return config;
});

export class ApiError extends Error {
  readonly status: number;
  readonly errorCode: string;
  readonly details: ApiErrorPayload["details"];
  readonly retryAfterSeconds: number | null;

  constructor(
    status: number,
    payload?: Partial<ApiErrorPayload>,
    retryAfterSeconds: number | null = null,
  ) {
    super(payload?.message ?? "خطای غیرمنتظره رخ داد.");
    this.name = "ApiError";
    this.status = status;
    this.errorCode = payload?.error_code ?? "INTERNAL_ERROR";
    this.details = payload?.details ?? [];
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

function parseRetryAfter(header: string | undefined): number | null {
  if (!header) return null;
  const asInt = Number(header);
  if (!Number.isNaN(asInt) && asInt > 0) return asInt;
  const dateMs = Date.parse(header);
  if (!Number.isNaN(dateMs)) {
    return Math.max(1, Math.ceil((dateMs - Date.now()) / 1000));
  }
  return null;
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<{ detail?: ApiErrorPayload } & Partial<ApiErrorPayload>>) => {
    const status = error.response?.status ?? 0;
    const original = error.config;

    if (
      status === 401 &&
      typeof window !== "undefined" &&
      original &&
      !(original as InternalAxiosRequestConfig & { _retry?: boolean })._retry
    ) {
      (original as InternalAxiosRequestConfig & { _retry?: boolean })._retry = true;
      const refreshed = await tryRefreshAccessToken();
      if (refreshed) {
        original.headers = original.headers ?? {};
        const next = getStoredToken();
        if (next) original.headers.Authorization = `Bearer ${next}`;
        return apiClient.request(original);
      }
      tokenStorage.clear();
      window.dispatchEvent(new Event("karzar-auth-change"));
      if (!window.location.pathname.startsWith("/login")) {
        const next = encodeURIComponent(window.location.pathname);
        window.location.href = `/login?next=${next}&expired=1`;
      }
    }

    const body = error.response?.data;
    const payload: ApiErrorPayload | undefined =
      (body?.detail as ApiErrorPayload | undefined) ??
      (body && "error_code" in body ? (body as ApiErrorPayload) : undefined);

    const retryAfter = parseRetryAfter(
      error.response?.headers?.["retry-after"] as string | undefined,
    );

    throw new ApiError(status, payload, retryAfter);
  },
);

/** Generate a UUID for Idempotency-Key headers. */
export function createIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `idem-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}
