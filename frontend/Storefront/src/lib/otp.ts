/**
 * Storefront OTP length — must match backend SEC-20 (6-digit codes).
 * Remote Karzar `otp_service._generate_otp_code` uses randbelow(1_000_000):06d.
 */
export const OTP_LENGTH = 6;

/** Mock / e2e fixed code (same length as live OTP). */
export const OTP_MOCK_CODE = "111111";
