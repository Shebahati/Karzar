/** Auth + step-up types mirrored from app/schemas/auth.py. */

export interface Token {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  expires_in: number;
}

export interface PinVerifyRequest {
  pin: string;
}

export interface StepUpTokenResponse {
  secure_token: string;
  token_type: "step_up";
  expires_in: number;
}
