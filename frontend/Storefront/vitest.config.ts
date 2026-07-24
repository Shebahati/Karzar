// @ts-nocheck
import { defineConfig } from "vitest/config";
import path from "node:path";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "happy-dom",
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    globals: false,
    env: {
      NEXT_PUBLIC_USE_MOCK: "true",
      NEXT_PUBLIC_API_BASE_URL: "http://127.0.0.1:8000/api/v1",
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
