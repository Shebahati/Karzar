/**
 * Production-mode HTTP status contract for entity existence (SEO Wave 1A).
 *
 * Requires a prior `next build` with NEXT_PUBLIC_USE_MOCK=true, then the
 * standalone server (`node .next/standalone/server.js`) — see package.json
 * script `test:http-contract` and playwright.http-contract.config.ts.
 */
import { expect, test } from "@playwright/test";

const BASE = process.env.HTTP_CONTRACT_BASE_URL ?? "http://127.0.0.1:3097";

async function statusOf(path: string): Promise<{
  status: number;
  location: string | null;
}> {
  const res = await fetch(`${BASE}${path}`, {
    method: "GET",
    redirect: "manual",
    headers: { "User-Agent": "KarzarHttpContract/1a" },
  });
  return {
    status: res.status,
    location: res.headers.get("location"),
  };
}

test.describe("entity HTTP status contract (production build + mock catalog)", () => {
  test("existing product slug → 200", async () => {
    const { status } = await statusOf("/product/bsh-gsb-13re");
    expect(status).toBe(200);
  });

  test("existing numeric product id → permanent redirect to slug", async () => {
    const { status, location } = await statusOf("/product/1");
    expect([301, 308]).toContain(status);
    expect(location).toMatch(/\/product\/bsh-gsb-13re$/);
  });

  test("missing product slug → 404", async () => {
    const { status } = await statusOf(
      "/product/definitely-missing-karzar-wave1a",
    );
    expect(status).toBe(404);
  });

  test("missing numeric product id → 404", async () => {
    const { status } = await statusOf("/product/999999999");
    expect(status).toBe(404);
  });

  test("existing category → 200", async () => {
    const { status } = await statusOf("/categories/kolis-mikrometr");
    expect(status).toBe(200);
  });

  test("missing category → 404", async () => {
    const { status } = await statusOf(
      "/categories/definitely-missing-karzar-wave1a",
    );
    expect(status).toBe(404);
  });

  test("existing empty category → 404 (current empty-hub contract)", async () => {
    const { status } = await statusOf("/categories/empty-test-category");
    expect(status).toBe(404);
  });

  test("existing indexable brand → 200", async () => {
    const { status } = await statusOf("/brands/bosch");
    expect(status).toBe(200);
  });

  test("existing thin brand (0 products) → 200 (policy preserved)", async () => {
    const { status } = await statusOf("/brands/empty-test-brand");
    expect(status).toBe(200);
  });

  test("missing brand → 404", async () => {
    const { status } = await statusOf(
      "/brands/definitely-missing-karzar-wave1a",
    );
    expect(status).toBe(404);
  });

  test("existing article → 200", async () => {
    const { status } = await statusOf("/blog/how-to-choose-drill");
    expect(status).toBe(200);
  });

  test("missing article → 404", async () => {
    const { status } = await statusOf(
      "/blog/definitely-missing-karzar-wave1a",
    );
    expect(status).toBe(404);
  });
});
