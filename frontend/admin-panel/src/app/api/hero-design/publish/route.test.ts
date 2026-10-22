import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

const { mkdir, writeFile } = vi.hoisted(() => ({
  mkdir: vi.fn(),
  writeFile: vi.fn(),
}));

vi.mock("fs", async (importOriginal) => {
  const actual = await importOriginal<typeof import("fs")>();
  return {
    ...actual,
    promises: {
      ...actual.promises,
      mkdir,
      writeFile,
    },
  };
});

import { POST } from "./route";

describe("POST /api/hero-design/publish", () => {
  const previousFlag = process.env.HERO_LEGACY_FILE_PUBLISH;

  beforeEach(() => {
    vi.clearAllMocks();
    delete process.env.HERO_LEGACY_FILE_PUBLISH;
  });

  afterEach(() => {
    if (previousFlag === undefined) {
      delete process.env.HERO_LEGACY_FILE_PUBLISH;
    } else {
      process.env.HERO_LEGACY_FILE_PUBLISH = previousFlag;
    }
  });

  it("returns 403 legacy_publish_disabled when HERO_LEGACY_FILE_PUBLISH is unset", async () => {
    const request = new Request("http://localhost/api/hero-design/publish", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        version: 1,
        publishedAt: "2026-01-01T00:00:00.000Z",
        slides: [],
      }),
    });

    const response = await POST(request);
    expect(response.status).toBe(403);

    const body = (await response.json()) as {
      error?: string;
      message_fa?: string;
    };
    expect(body.error).toBe("legacy_publish_disabled");
    expect(body.message_fa).toMatch(/انتشار مستقیم غیرفعال/);
    expect(mkdir).not.toHaveBeenCalled();
    expect(writeFile).not.toHaveBeenCalled();
  });
});
