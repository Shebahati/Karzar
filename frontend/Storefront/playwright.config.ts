import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "on-first-retry",
    locale: "fa-IR",
  },
  webServer: {
    command: "npm run dev -- --port 3000 --hostname 127.0.0.1",
    url: "http://127.0.0.1:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      ...process.env,
      NEXT_PUBLIC_USE_MOCK: "true",
      NEXT_PUBLIC_MOCK_LATENCY_MS: "0",
      NEXT_PUBLIC_API_BASE_URL: "http://127.0.0.1:8000/api/v1",
    },
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
