import { createRoot } from "react-dom/client";
import { act, type ReactNode } from "react";
import { afterEach, describe, expect, it } from "vitest";
import { CheckoutPolicyNotice } from "@/components/checkout/checkout-policy-notice";

function renderIntoContainer(node: ReactNode) {
  const container = document.createElement("div");
  document.body.appendChild(container);
  act(() => {
    createRoot(container).render(node);
  });
  return container;
}

describe("CheckoutPolicyNotice", () => {
  let container: HTMLDivElement;

  afterEach(() => {
    container?.remove();
  });

  it("links to Terms and Privacy without blocking semantics", () => {
    container = renderIntoContainer(<CheckoutPolicyNotice />);
    const terms = container.querySelector<HTMLAnchorElement>('a[href="/terms"]');
    const privacy = container.querySelector<HTMLAnchorElement>('a[href="/privacy"]');
    expect(terms).not.toBeNull();
    expect(privacy).not.toBeNull();
    expect(terms?.tagName).toBe("A");
    expect(privacy?.tagName).toBe("A");
  });
});
