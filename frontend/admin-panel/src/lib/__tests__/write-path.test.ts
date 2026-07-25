import { beforeEach, describe, expect, it, vi } from "vitest";

const mockPost = vi.fn();
const mockGet = vi.fn();
const mockPut = vi.fn();

vi.mock("axios", () => {
  const instance = {
    post: mockPost,
    get: mockGet,
    put: mockPut,
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
    defaults: { headers: { common: {} } },
  };
  return {
    default: {
      create: () => instance,
      post: mockPost,
      isAxiosError: (err: unknown) =>
        Boolean(err && typeof err === "object" && "isAxiosError" in err),
    },
  };
});

vi.mock("@/config/env", () => ({
  env: {
    USE_MOCK: false,
    API_BASE_URL: "http://localhost:8000/api/v1",
  },
}));

describe("admin write-path helpers", () => {
  beforeEach(() => {
    vi.resetModules();
    mockPost.mockReset();
    mockGet.mockReset();
    mockPut.mockReset();
  });

  it("stores access token in memory tokenStorage", async () => {
    const { tokenStorage, tryRefreshAccessToken } = await import("@/lib/api-client");
    tokenStorage.set("fresh-access", 3600, "refresh-token");
    expect(tokenStorage.getAccessToken()).toBe("fresh-access");

    mockPost.mockResolvedValueOnce({
      data: {
        access_token: "rotated-access",
        refresh_token: "refresh-token",
        expires_in: 3600,
      },
    });
    const ok = await tryRefreshAccessToken();
    expect(ok).toBe(true);
    expect(tokenStorage.getAccessToken()).toBe("rotated-access");
  });

  it("maps availability toggle payload shape", async () => {
    mockPut.mockResolvedValueOnce({
      data: {
        id: 7,
        sku: "SKU-7",
        stock_unit: "piece",
        is_available: true,
        availability: true,
        stock_status: "in_stock",
      },
    });
    const { catalogService } = await import("@/services/catalog");
    const result = await catalogService.setProductAvailability(7, {
      is_available: true,
      reason: "restocked",
    });
    expect(mockPut).toHaveBeenCalled();
    expect(result.availability).toBe(true);
  });

  it("calls binary bulk availability endpoint", async () => {
    mockPut.mockResolvedValueOnce({ data: { updated_product_ids: [1, 2] } });
    const { catalogService } = await import("@/services/catalog");
    const result = await catalogService.bulkSetAvailability(
      [
        { product_id: 1, is_available: true, reason: "restock" },
        { product_id: 2, is_available: false, reason: "restock" },
      ],
      "step-up-token",
    );
    expect(mockPut).toHaveBeenCalledWith(
      "/products/bulk/availability",
      {
        items: [
          { product_id: 1, is_available: true, reason: "restock" },
          { product_id: 2, is_available: false, reason: "restock" },
        ],
      },
      expect.objectContaining({
        headers: expect.objectContaining({ "X-Step-Up-Token": "step-up-token" }),
      }),
    );
    expect(result.updated_product_ids).toEqual([1, 2]);
  });
});
