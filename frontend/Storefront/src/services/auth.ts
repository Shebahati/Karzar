import {
  clearCartToken,
  getCartToken,
  getStoredToken,
  setStoredToken,
  tokenStorage,
} from "@/lib/api-client";
import { clearPendingPayment } from "@/lib/pending-payment";
import { getMockApi } from "@/lib/get-mock-api";
import { env } from "@/config/env";
import { cartService } from "@/services/cart";
import { useCartStore } from "@/store/cart-store";
import type {
  MeResponse,
  OtpRequestPayload,
  OtpRequestResponse,
  OtpVerifyPayload,
  OtpVerifyResponse,
} from "@/types/auth";
import { apiClient } from "@/lib/api-client";

interface MeBackendResponse {
  id: number;
  phone_number: string;
  full_name: string | null;
  role?: string;
  is_b2b?: boolean;
  company_name?: string | null;
}

function mapMe(data: MeBackendResponse): MeResponse {
  return {
    id: data.id,
    phone: data.phone_number,
    full_name: data.full_name,
    role: data.role,
    is_b2b: data.is_b2b,
    company_name: data.company_name,
  };
}

async function syncCartAfterLogin(): Promise<string | null> {
  try {
    const guestToken = getCartToken();
    if (guestToken) {
      await cartService.merge(guestToken);
      clearCartToken();
    }
    const result = await useCartStore.getState().reconcileFromServer();
    return result.ok ? null : (result.error ?? "همگام‌سازی سبد ناموفق بود.");
  } catch {
    const message = "همگام‌سازی سبد با سرور ناموفق بود. سبد محلی حفظ شد.";
    useCartStore.getState().clearSyncError();
    useCartStore.setState({ lastSyncError: message });
    return message;
  }
}

export const authService = {
  async requestOtp(payload: OtpRequestPayload): Promise<OtpRequestResponse> {
    if (env.USE_MOCK) return (await getMockApi()).requestOtp(payload);
    // Backend OtpRequest expects `phone`, not `phone_number`.
    const { data } = await apiClient.post<OtpRequestResponse>("/auth/otp/request", {
      phone: payload.phone,
    });
    return { ...data, phone: data.phone ?? payload.phone };
  },

  async verifyOtp(payload: OtpVerifyPayload): Promise<OtpVerifyResponse> {
    const result = env.USE_MOCK
      ? await (await getMockApi()).verifyOtp(payload)
      : (
          await apiClient.post<OtpVerifyResponse>("/auth/otp/verify", {
            phone: payload.phone,
            code: payload.code,
          })
        ).data;

    const normalized: OtpVerifyResponse = {
      access_token: result.access_token,
      refresh_token: result.refresh_token ?? "",
      token_type: result.token_type ?? "bearer",
      expires_in: result.expires_in ?? 1800,
      customer: {
        id: result.customer.id,
        phone: result.customer.phone ?? payload.phone,
        full_name: result.customer.full_name,
      },
    };

    setStoredToken(
      normalized.access_token,
      normalized.expires_in,
      normalized.refresh_token || null,
    );

    if (typeof window !== "undefined") {
      window.localStorage.setItem(
        "karzar.storefront.customer",
        JSON.stringify(normalized.customer),
      );
      window.dispatchEvent(new Event("karzar-auth-change"));
    }

    let cart_sync_error: string | null = null;
    if (!env.USE_MOCK) {
      cart_sync_error = await syncCartAfterLogin();
    }

    return { ...normalized, cart_sync_error };
  },

  async getMe(): Promise<MeResponse> {
    if (env.USE_MOCK) return (await getMockApi()).getMe();
    const { data } = await apiClient.get<MeBackendResponse>("/auth/me");
    return mapMe(data);
  },

  async logout(): Promise<void> {
    if (!env.USE_MOCK) {
      try {
        await apiClient.post("/auth/logout");
      } catch {
        // Ignore network errors on logout; still clear local session.
      }
    }
    setStoredToken(null);
    if (typeof window !== "undefined") {
      window.localStorage.removeItem("karzar.storefront.customer");
      clearPendingPayment();
      window.dispatchEvent(new Event("karzar-auth-change"));
    }
  },

  async requestPasswordReset(phone: string): Promise<{ ok: boolean; expires_in?: number }> {
    if (env.USE_MOCK) return { ok: true, expires_in: 120 };
    const { data } = await apiClient.post<{ ok?: boolean; expires_in?: number }>(
      "/auth/password-reset/request",
      { phone },
    );
    return { ok: true, expires_in: data.expires_in };
  },

  async confirmPasswordReset(payload: {
    phone: string;
    code: string;
    new_password: string;
  }): Promise<{ ok: boolean }> {
    if (env.USE_MOCK) return { ok: true };
    const { data } = await apiClient.post<{ ok: boolean }>(
      "/auth/password-reset/confirm",
      payload,
    );
    return data;
  },

  async changePassword(payload: {
    current_password: string;
    new_password: string;
  }): Promise<{ ok: boolean }> {
    if (env.USE_MOCK) return { ok: true };
    const { data } = await apiClient.post<{ ok: boolean }>("/auth/change-password", payload);
    return data;
  },
};

export { tokenStorage };
