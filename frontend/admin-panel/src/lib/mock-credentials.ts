/**
 * Mock-only admin login hints. Imported dynamically when USE_MOCK is true
 * so production live bundles never include these strings from the login form.
 */
export const MOCK_ADMIN_CREDENTIALS = {
  phone: "09120000000",
  passwordHint: "Admin@123456",
} as const;
