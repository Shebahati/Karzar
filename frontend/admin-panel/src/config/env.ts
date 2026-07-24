/**
 * Runtime configuration sourced from public env vars.
 *
 * `USE_MOCK` lets the admin panel run fully offline against the in-memory
 * mock layer while the FastAPI backend is being built in parallel. Flip
 * `NEXT_PUBLIC_USE_MOCK=false` (and point `NEXT_PUBLIC_API_BASE_URL` at the
 * live server) to switch every data hook to real HTTP with zero code changes.
 */
export const env = {
  API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1",
  // Default false: live API. Set NEXT_PUBLIC_USE_MOCK=true for offline mocks.
  USE_MOCK: (process.env.NEXT_PUBLIC_USE_MOCK ?? "false").toLowerCase() === "true",
  /** Simulated network latency (ms) for the mock layer. */
  MOCK_LATENCY_MS: Number(process.env.NEXT_PUBLIC_MOCK_LATENCY_MS ?? 650),
} as const;
