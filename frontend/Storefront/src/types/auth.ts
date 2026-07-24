/** Auth types for the storefront OTP login flow — aligned with app/schemas/auth.py. */

export interface OtpRequestPayload {
  phone: string;
}

export interface OtpRequestResponse {
  phone: string;
  expires_in: number;
  /** Dev-only echo of the code; never returned in production. */
  dev_code?: string;
}

export interface OtpVerifyPayload {
  phone: string;
  code: string;
}

export interface OtpVerifyResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  customer: {
    id: number;
    phone: string;
    full_name: string | null;
  };
  /** Set when guest→auth cart merge / GET reconcile fails (non-blocking). */
  cart_sync_error?: string | null;
}

export interface MeResponse {
  id: number;
  phone: string;
  full_name: string | null;
  role?: string;
  is_b2b?: boolean;
  company_name?: string | null;
}

export interface RefreshTokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}
