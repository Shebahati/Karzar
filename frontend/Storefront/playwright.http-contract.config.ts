import { defineConfig } from "@playwright/test";

/**
 * HTTP contract against `next start` (production build), not `next dev`.
 * Build first with the same env as webServer (see package.json).
 */
export default defineConfig({
  testDir: "./e2e",
  testMatch: "entity-http-status.spec.ts",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  timeout: 60_000,
  use: {
    baseURL: "http://127.0.0.1:3011",
    extraHTTPHeaders: { "User-Agent": "KarzarHttpContract/1a" },
  },
  webServer: {
    command: "npm run start -- --port 3011 --hostname 127.0.0.1",
    url: "http://127.0.0.1:3011",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      ...process.env,
      NEXT_PUBLIC_USE_MOCK: "true",
      NEXT_PUBLIC_MOCK_LATENCY_MS: "0",
      NEXT_PUBLIC_API_BASE_URL: "http://127.0.0.1:8000/api/v1",
      NEXT_PUBLIC_SITE_URL: "https://www.karzartools.com",
      HTTP_CONTRACT_BASE_URL: "http://127.0.0.1:3011",
    },
  },
});
