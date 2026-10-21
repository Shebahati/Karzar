import { createRoot } from "react-dom/client";
import { act, type ReactNode } from "react";
import { afterEach, describe, expect, it } from "vitest";
import { CuratedCategoryIconImg } from "@/components/ui/curated-category-icon-img";

function renderIntoContainer(node: ReactNode) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  act(() => {
    createRoot(container).render(node);
  });
  return container;
}

describe("CuratedCategoryIconImg", () => {
  const prev = process.env.NEXT_PUBLIC_CATEGORY_ICON_WEBP;

  afterEach(() => {
    process.env.NEXT_PUBLIC_CATEGORY_ICON_WEBP = prev;
    document.body.innerHTML = "";
  });

  it("flag off: forwards explicit loading, fetchPriority, and decoding", () => {
    process.env.NEXT_PUBLIC_CATEGORY_ICON_WEBP = "0";
    const container = renderIntoContainer(
      <CuratedCategoryIconImg
        src="/category-icons/insert.png"
        loading="lazy"
        fetchPriority="low"
        decoding="sync"
        alt="x"
      />,
    );
    const img = container.querySelector("img");
    expect(img).toBeTruthy();
    expect(container.querySelector("picture")).toBeNull();
    expect(img!.getAttribute("src")).toBe("/category-icons/insert.png");
    expect(img!.getAttribute("loading")).toBe("lazy");
    expect(img!.getAttribute("fetchpriority")).toBe("low");
    expect(img!.getAttribute("decoding")).toBe("sync");
  });

  it("flag on allowlisted: forwards attributes on png fallback img inside picture", () => {
    process.env.NEXT_PUBLIC_CATEGORY_ICON_WEBP = "1";
    const container = renderIntoContainer(
      <CuratedCategoryIconImg
        src="/category-icons/takhfif.png"
        loading="eager"
        fetchPriority="high"
        decoding="sync"
        alt=""
        width={28}
        height={28}
      />,
    );
    const picture = container.querySelector("picture");
    const source = container.querySelector("source[type='image/webp']");
    const img = container.querySelector("img");
    expect(picture).toBeTruthy();
    expect(source!.getAttribute("srcset")).toBe("/category-icons/webp/takhfif.webp");
    expect(img!.getAttribute("src")).toBe("/category-icons/takhfif.png");
    expect(img!.getAttribute("loading")).toBe("eager");
    expect(img!.getAttribute("fetchpriority")).toBe("high");
    expect(img!.getAttribute("decoding")).toBe("sync");
  });

  it("flag on allowlisted: defaults decoding to async when omitted", () => {
    process.env.NEXT_PUBLIC_CATEGORY_ICON_WEBP = "1";
    const container = renderIntoContainer(
      <CuratedCategoryIconImg src="/category-icons/insert.png" alt="" width={28} height={28} />,
    );
    const img = container.querySelector("img");
    expect(img!.getAttribute("decoding")).toBe("async");
    expect(img!.hasAttribute("loading")).toBe(false);
    expect(img!.hasAttribute("fetchpriority")).toBe(false);
  });

  it("flag off: omits loading and fetchPriority when not provided", () => {
    process.env.NEXT_PUBLIC_CATEGORY_ICON_WEBP = "0";
    const container = renderIntoContainer(
      <CuratedCategoryIconImg src="/category-icons/takhfif.png" alt="icon" width={28} height={28} />,
    );
    const img = container.querySelector("img");
    expect(img!.getAttribute("src")).toBe("/category-icons/takhfif.png");
    expect(img!.hasAttribute("loading")).toBe(false);
    expect(img!.hasAttribute("fetchpriority")).toBe(false);
    expect(img!.hasAttribute("decoding")).toBe(false);
  });

  it("flag on: unknown category-icons path stays plain img without picture", () => {
    process.env.NEXT_PUBLIC_CATEGORY_ICON_WEBP = "1";
    const container = renderIntoContainer(
      <CuratedCategoryIconImg
        src="/category-icons/custom-future.png"
        loading="lazy"
        alt=""
      />,
    );
    expect(container.querySelector("picture")).toBeNull();
    const img = container.querySelector("img");
    expect(img!.getAttribute("src")).toBe("/category-icons/custom-future.png");
    expect(img!.getAttribute("loading")).toBe("lazy");
  });

  it("flag on: external url stays plain img", () => {
    process.env.NEXT_PUBLIC_CATEGORY_ICON_WEBP = "1";
    const external = "https://cdn.example.com/icon.png";
    const container = renderIntoContainer(
      <CuratedCategoryIconImg src={external} fetchPriority="low" alt="" />,
    );
    expect(container.querySelector("picture")).toBeNull();
    const img = container.querySelector("img");
    expect(img!.getAttribute("src")).toBe(external);
    expect(img!.getAttribute("fetchpriority")).toBe("low");
  });

  it("preserves width, height, className and alt", () => {
    process.env.NEXT_PUBLIC_CATEGORY_ICON_WEBP = "0";
    const container = renderIntoContainer(
      <CuratedCategoryIconImg
        src="/other-icons/foo.png"
        alt="label"
        width={40}
        height={40}
        className="h-6 w-6"
      />,
    );
    const img = container.querySelector("img");
    expect(img!.getAttribute("width")).toBe("40");
    expect(img!.getAttribute("height")).toBe("40");
    expect(img!.className).toContain("h-6");
    expect(img!.getAttribute("alt")).toBe("label");
  });
});
