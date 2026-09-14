import { createRoot } from "react-dom/client";
import { act } from "react";
import { afterEach, describe, expect, it } from "vitest";
import { SiteFooter } from "@/components/layout/site-footer";

const ENAMAD_TRUST_URL =
  "https://trustseal.enamad.ir/?id=6961566&Code=5F01NsyiqBFfBjNyzpNxr70bt4r065sr";

describe("SiteFooter eNamad trust seal", () => {
  let container: HTMLDivElement;

  afterEach(() => {
    container?.remove();
  });

  it("uses official trust URL, origin referrer policy, and noopener without noreferrer", () => {
    container = document.createElement("div");
    document.body.appendChild(container);

    act(() => {
      createRoot(container).render(<SiteFooter />);
    });

    const enamad = container.querySelector<HTMLAnchorElement>(
      `a[href="${ENAMAD_TRUST_URL}"]`,
    );

    expect(enamad).not.toBeNull();
    expect(enamad?.getAttribute("referrerpolicy")).toBe("origin");
    expect(enamad?.target).toBe("_blank");
    expect(enamad?.rel).toBe("noopener");
    expect(enamad?.rel).not.toContain("noreferrer");
  });
});
