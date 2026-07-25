import { beforeEach, describe, expect, it, vi } from "vitest";

import { stepUpPinSchema } from "@/lib/validation";

const postMock = vi.fn();

vi.mock("@/config/env", () => ({
  env: { USE_MOCK: false, API_BASE_URL: "http://localhost:8000/api/v1" },
}));

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    post: (...args: unknown[]) => postMock(...args),
  },
}));

describe("step-up PIN client flow", () => {
  beforeEach(() => {
    vi.resetModules();
    postMock.mockReset();
  });

  it("validates PIN length before verify call", () => {
    expect(() => stepUpPinSchema.parse("12")).toThrow();
    expect(stepUpPinSchema.parse("84729101")).toBe("84729101");
  });

  it("catalogService.verifyPin posts PIN and returns secure token", async () => {
    postMock.mockResolvedValueOnce({
      data: { secure_token: "step-up-abc", expires_in: 120 },
    });

    const { catalogService } = await import("@/services/catalog");
    const result = await catalogService.verifyPin("84729101");

    expect(postMock).toHaveBeenCalledWith("/auth/verify-pin", { pin: "84729101" });
    expect(result.secure_token).toBe("step-up-abc");
  });
});
