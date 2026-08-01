import { describe, expect, it } from "vitest";
import {
  isSafeNextImageSrc,
  toSafeNextImageSrc,
} from "@/lib/image-remote-patterns";

describe("toSafeNextImageSrc", () => {
  it("allows local public paths", () => {
    expect(toSafeNextImageSrc("/images/placeholders/karzar-editorial.svg")).toBe(
      "/images/placeholders/karzar-editorial.svg",
    );
  });

  it("rejects picsum even when otherwise remote", () => {
    expect(toSafeNextImageSrc("https://picsum.photos/seed/karzar-36/800/600")).toBeNull();
    expect(isSafeNextImageSrc("https://picsum.photos/seed/karzar-36/800/600")).toBe(false);
  });

  it("allows configured API upload host", () => {
    expect(toSafeNextImageSrc("http://localhost:8000/static/uploads/p.jpg")).toBe(
      "http://localhost:8000/static/uploads/p.jpg",
    );
  });

  it("rejects unconfigured remote hosts", () => {
    expect(toSafeNextImageSrc("https://evil.example/x.jpg")).toBeNull();
  });

  it("rejects empty / invalid", () => {
    expect(toSafeNextImageSrc(null)).toBeNull();
    expect(toSafeNextImageSrc("")).toBeNull();
    expect(toSafeNextImageSrc("not-a-url")).toBeNull();
  });
});
