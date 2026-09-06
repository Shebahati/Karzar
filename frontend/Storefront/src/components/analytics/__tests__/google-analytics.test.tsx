import { afterEach, describe, expect, it, vi } from "vitest";
import type { ReactElement, ReactNode } from "react";

type ScriptProbe = {
  src?: string;
  id?: string;
  children?: string;
};

function collectScripts(node: ReactNode): ScriptProbe[] {
  if (node == null || typeof node === "boolean") return [];
  if (Array.isArray(node)) return node.flatMap(collectScripts);
  if (typeof node !== "object") return [];

  const element = node as ReactElement<{
    src?: string;
    id?: string;
    children?: ReactNode;
  }>;
  const props = element.props ?? {};
  const here: ScriptProbe[] = [];
  if (typeof props.src === "string" || typeof props.id === "string") {
    here.push({
      src: typeof props.src === "string" ? props.src : undefined,
      id: typeof props.id === "string" ? props.id : undefined,
      children: typeof props.children === "string" ? props.children : undefined,
    });
  }
  return [...here, ...collectScripts(props.children)];
}

async function loadGoogleAnalytics() {
  return import("@/components/analytics/google-analytics");
}

async function loadGoogleTagManager() {
  return import("@/components/analytics/google-tag-manager");
}

describe("GoogleAnalytics install cases", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it("Case A: emits the GA4 gtag when measurement ID is set and GTM is absent", async () => {
    vi.stubEnv("NEXT_PUBLIC_GA_MEASUREMENT_ID", "G-NT8ZT3G6HC");
    vi.stubEnv("NEXT_PUBLIC_GTM_ID", "");

    const { GoogleAnalytics, GA_MEASUREMENT_ID } = await loadGoogleAnalytics();
    const { GoogleTagManagerHead, GoogleTagManagerNoscript } =
      await loadGoogleTagManager();

    expect(GA_MEASUREMENT_ID).toBe("G-NT8ZT3G6HC");

    const tree = GoogleAnalytics({ nonce: "test-nonce" });
    const scripts = collectScripts(tree);
    const loader = scripts.find((s) => s.src?.includes("gtag/js"));
    const config = scripts.find((s) => s.id === "google-analytics-gtag");

    expect(loader?.src).toBe(
      "https://www.googletagmanager.com/gtag/js?id=G-NT8ZT3G6HC",
    );
    expect(config?.children).toContain("gtag('config', 'G-NT8ZT3G6HC')");
    expect(GoogleTagManagerHead({})).toBeNull();
    expect(GoogleTagManagerNoscript()).toBeNull();
  });

  it("Case B: emits no Google Analytics script when neither ID is configured", async () => {
    vi.stubEnv("NEXT_PUBLIC_GA_MEASUREMENT_ID", "");
    vi.stubEnv("NEXT_PUBLIC_GTM_ID", "");

    const { GoogleAnalytics, GA_MEASUREMENT_ID } = await loadGoogleAnalytics();
    const { GoogleTagManagerHead, GoogleTagManagerNoscript } =
      await loadGoogleTagManager();

    expect(GA_MEASUREMENT_ID).toBe("");
    expect(GoogleAnalytics({})).toBeNull();
    expect(GoogleTagManagerHead({})).toBeNull();
    expect(GoogleTagManagerNoscript()).toBeNull();
  });

  it("Case C: does not emit direct GA4 when GTM is configured", async () => {
    vi.stubEnv("NEXT_PUBLIC_GA_MEASUREMENT_ID", "G-NT8ZT3G6HC");
    vi.stubEnv("NEXT_PUBLIC_GTM_ID", "GTM-TESTONLY");

    const { GoogleAnalytics } = await loadGoogleAnalytics();
    const { GoogleTagManagerHead } = await loadGoogleTagManager();

    expect(GoogleAnalytics({})).toBeNull();

    const gtmScripts = collectScripts(GoogleTagManagerHead({}));
    expect(gtmScripts.some((s) => s.id === "google-tag-manager")).toBe(true);
    expect(gtmScripts.some((s) => s.src?.includes("gtag/js?id="))).toBe(false);
  });
});
