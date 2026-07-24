import axios from "axios";

import { env } from "@/config/env";

export interface HealthResponse {
  status: string;
  [key: string]: unknown;
}

export interface ReadyResponse {
  status: string;
  database?: string;
  redis?: string;
  checks?: Record<string, string>;
  [key: string]: unknown;
}

function apiOrigin(): string {
  try {
    const url = new URL(env.API_BASE_URL);
    return `${url.protocol}//${url.host}`;
  } catch {
    return "http://localhost:8000";
  }
}

/**
 * Ops health probes live outside `/api/v1` (GET /health, GET /ready).
 * Used only in the admin dashboard status strip — not the storefront.
 */
export const systemService = {
  async getHealth(): Promise<HealthResponse> {
    if (env.USE_MOCK) return { status: "ok", mode: "mock" };
    const { data } = await axios.get<HealthResponse>(`${apiOrigin()}/health`, {
      timeout: 8_000,
    });
    return data;
  },

  async getReady(): Promise<ReadyResponse> {
    if (env.USE_MOCK) {
      return { status: "ready", checks: { database: "ok", redis: "ok" } };
    }
    const { data } = await axios.get<ReadyResponse>(`${apiOrigin()}/ready`, {
      timeout: 8_000,
    });
    return data;
  },
};
