import { describe, expect, it } from "vitest";

import {
  productFormDefaults,
  toProductCreatePayload,
  toProductUpdatePayload,
} from "./product-schema";

describe("brand integrity in catalog form payloads", () => {
  it("omits a blank brand on edit, avoiding a destructive brand_id=null PUT", () => {
    const payload = toProductUpdatePayload({ ...productFormDefaults, brand_id: "" });
    expect(payload).not.toHaveProperty("brand_id");
    expect(payload).not.toHaveProperty("is_available");
  });

  it("sends an intentionally selected brand on edit", () => {
    const payload = toProductUpdatePayload({ ...productFormDefaults, brand_id: "3" });
    expect(payload.brand_id).toBe(3);
  });

  it("retains nullable brand behavior on create", () => {
    const payload = toProductCreatePayload({ ...productFormDefaults, brand_id: "" });
    expect(payload.brand_id).toBeNull();
  });
});
