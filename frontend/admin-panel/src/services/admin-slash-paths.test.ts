import { beforeEach, describe, expect, it, vi } from "vitest";

const { get } = vi.hoisted(() => ({
  get: vi.fn(),
}));

vi.mock("@/config/env", () => ({
  env: { USE_MOCK: false },
}));

vi.mock("@/lib/api-client", () => ({
  apiClient: { get },
  withStepUp: vi.fn(),
}));

vi.mock("@/lib/get-mock-api", () => ({
  getMockApi: vi.fn(),
}));

import { customersService } from "@/services/customers";
import { ordersService } from "@/services/orders";

describe("admin collection API paths", () => {
  beforeEach(() => {
    get.mockReset();
  });

  it("requests the orders collection without a trailing slash", async () => {
    get.mockResolvedValueOnce({ data: { data: [], meta: {} } });

    await ordersService.list();

    expect(get).toHaveBeenCalledWith("/orders", { params: {} });
  });

  it("requests the users collection without a trailing slash", async () => {
    get.mockResolvedValueOnce({ data: { data: [], meta: {} } });

    await customersService.list();

    expect(get).toHaveBeenCalledWith("/users", { params: {} });
  });
});
