import { env } from "@/config/env";
import { getMockApi } from "@/lib/get-mock-api";
import { apiClient, tokenStorage } from "@/lib/api-client";
import { clearAdminSessionCookie, setAdminSessionCookie } from "@/lib/session-cookie";
import type { Token } from "@/types/auth";

export interface LoginPayload {
  phone_number: string;
  password: string;
}

export interface AdminMeResponse {
  id: number;
  phone_number: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  company_name?: string | null;
  is_b2b?: boolean;
}

const ADMIN_ROLES = new Set(["super_admin"]);

/**
 * Authenticate with the FastAPI OAuth2 login endpoint.
 * FastAPI expects `username` (phone) + `password` as form-urlencoded.
 */
export const authService = {
  async login(payload: LoginPayload): Promise<Token> {
    if (env.USE_MOCK) {
      const mockApi = await getMockApi();
      const data = await mockApi.login(payload);
      tokenStorage.set(data.access_token, data.expires_in, data.refresh_token ?? "mock-refresh");
      await setAdminSessionCookie(data.access_token);
      return data;
    }

    const body = new URLSearchParams();
    body.set("username", payload.phone_number.trim());
    body.set("password", payload.password);

    const { data } = await apiClient.post<Token>("/auth/login", body, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });

    tokenStorage.set(data.access_token, data.expires_in, data.refresh_token ?? null);
    await setAdminSessionCookie(data.access_token);
    return data;
  },

  async getMe(): Promise<AdminMeResponse> {
    if (env.USE_MOCK) {
      const { MOCK_ADMIN_CREDENTIALS } = await import("@/lib/mock-credentials");
      return {
        id: 1,
        phone_number: MOCK_ADMIN_CREDENTIALS.phone,
        full_name: "سوپر ادمین",
        role: "super_admin",
        is_active: true,
      };
    }
    const { data } = await apiClient.get<AdminMeResponse>("/auth/me");
    return data;
  },

  isAdminRole(role: string | null | undefined): boolean {
    return Boolean(role && ADMIN_ROLES.has(role));
  },

  /**
   * Confirms /auth/me returns super_admin (cookie and/or memory token).
   * Clears session on failure.
   */
  async assertAdminSession(): Promise<AdminMeResponse> {
    if (env.USE_MOCK) {
      if (!this.isAuthenticated()) {
        throw new Error("UNAUTHENTICATED");
      }
      await setAdminSessionCookie(tokenStorage.getAccessToken());
      return this.getMe();
    }

    try {
      const me = await this.getMe();
      if (!me.is_active || !this.isAdminRole(me.role)) {
        await this.logout();
        throw new Error("FORBIDDEN");
      }
      const access = tokenStorage.getAccessToken();
      if (access) await setAdminSessionCookie(access);
      return me;
    } catch (err) {
      if (err instanceof Error && (err.message === "FORBIDDEN" || err.message === "UNAUTHENTICATED")) {
        throw err;
      }
      throw new Error("UNAUTHENTICATED");
    }
  },

  async logout() {
    if (!env.USE_MOCK && typeof window !== "undefined") {
      try {
        await apiClient.post("/auth/logout");
      } catch {
        // Still clear local session.
      }
    }
    tokenStorage.clear();
    await clearAdminSessionCookie();
    if (typeof window !== "undefined") {
      window.localStorage.removeItem("token");
      window.sessionStorage.clear();
    }
  },

  isAuthenticated(): boolean {
    if (typeof window === "undefined") return false;
    if (env.USE_MOCK) {
      return Boolean(window.localStorage.getItem("karzar.access_token"));
    }
    return Boolean(tokenStorage.getAccessToken());
  },
};
