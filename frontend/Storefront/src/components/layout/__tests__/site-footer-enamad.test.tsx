import { createRoot } from "react-dom/client";
import { act, type ReactNode } from "react";
import { afterEach, describe, expect, it } from "vitest";
import { FooterCredentials } from "@/components/layout/footer-credentials";
import { SiteFooter } from "@/components/layout/site-footer";
import {
  BUSINESS_LICENSE_ONLINE,
  BUSINESS_LICENSE_PHYSICAL,
  ENAMAD_CREDENTIAL,
} from "@/config/trust-credentials";

const ENAMAD_TRUST_URL =
  "https://trustseal.enamad.ir/?id=6961566&Code=5F01NsyiqBFfBjNyzpNxr70bt4r065sr";
const ENAMAD_LOGO_URL =
  "https://trustseal.enamad.ir/logo.aspx?id=6961566&Code=5F01NsyiqBFfBjNyzpNxr70bt4r065sr";

function renderIntoContainer(node: ReactNode) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  act(() => {
    createRoot(container).render(node);
  });
  return container;
}

describe("SiteFooter eNamad trust seal", () => {
  let container: HTMLDivElement;

  afterEach(() => {
    container?.remove();
  });

  it("uses official trust URL, origin referrer policy, and noopener without noreferrer", () => {
    container = renderIntoContainer(<SiteFooter />);

    const enamadLinks = container.querySelectorAll<HTMLAnchorElement>(
      `a[href="${ENAMAD_TRUST_URL}"]`,
    );
    expect(enamadLinks).toHaveLength(1);

    const enamad = enamadLinks[0];
    expect(enamad.getAttribute("referrerpolicy")).toBe("origin");
    expect(enamad.target).toBe("_blank");
    expect(enamad.rel).toBe("noopener");
    expect(enamad.rel).not.toContain("noreferrer");
    expect(enamad.getAttribute("aria-label")).toBe(
      "استعلام نماد اعتماد الکترونیکی کارزار",
    );

    const img = enamad.querySelector("img");
    expect(img?.getAttribute("src")).toBe(ENAMAD_LOGO_URL);
    expect(img?.getAttribute("referrerpolicy")).toBe("origin");
    expect(img?.getAttribute("code")).toBe(ENAMAD_CREDENTIAL.enamadCode);
    expect(img?.getAttribute("width")).toBe("80");
    expect(img?.getAttribute("height")).toBe("90");
  });

  it("groups Enamad under مجوزها و اعتبارها and does not duplicate it", () => {
    container = renderIntoContainer(<SiteFooter />);

    const heading = container.querySelector("#footer-credentials-heading");
    expect(heading?.textContent).toBe("مجوزها و اعتبارها");

    const section = heading?.closest("section");
    expect(section?.querySelector(`a[href="${ENAMAD_TRUST_URL}"]`)).not.toBeNull();
    expect(section?.getAttribute("dir")).toBe("rtl");

    expect(container.textContent).not.toContain("پروانه کسب مجازی");
    expect(container.textContent).not.toContain("پروانه کسب حضوری");
  });
});

describe("FooterCredentials", () => {
  let container: HTMLDivElement;

  afterEach(() => {
    container?.remove();
  });

  it("renders business-license cards only when official https URLs are provided", () => {
    container = renderIntoContainer(
      <FooterCredentials
        credentials={[
          ENAMAD_CREDENTIAL,
          {
            ...BUSINESS_LICENSE_ONLINE,
            verificationUrl: "https://verify.test.invalid/online",
          },
          {
            ...BUSINESS_LICENSE_PHYSICAL,
            verificationUrl: "https://verify.test.invalid/physical",
          },
        ]}
      />,
    );

    const online = container.querySelector<HTMLAnchorElement>(
      'a[href="https://verify.test.invalid/online"]',
    );
    const physical = container.querySelector<HTMLAnchorElement>(
      'a[href="https://verify.test.invalid/physical"]',
    );

    expect(online?.rel).toBe("noopener noreferrer");
    expect(online?.target).toBe("_blank");
    expect(online?.getAttribute("aria-label")).toBe(
      "استعلام پروانه کسب مجازی کارزار",
    );
    expect(physical?.rel).toBe("noopener noreferrer");
    expect(physical?.getAttribute("aria-label")).toBe(
      "استعلام پروانه کسب حضوری کارزار",
    );

    const titles = [...container.querySelectorAll("a span[aria-hidden]")]
      .map((el) => el.textContent)
      .filter(Boolean);
    expect(titles).toContain("پروانه کسب مجازی");
    expect(titles).toContain("پروانه کسب حضوری");
    expect(titles).toContain("مشاهده و استعلام");
  });

  it("does not create a clickable card without a verification URL", () => {
    container = renderIntoContainer(
      <FooterCredentials credentials={[BUSINESS_LICENSE_ONLINE]} />,
    );
    expect(container.querySelector("a")).toBeNull();
    expect(container.textContent).toBe("");
  });
});
