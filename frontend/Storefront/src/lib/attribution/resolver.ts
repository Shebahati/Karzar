import type { AcquisitionTouch, AttributionState } from "./types";

function hostFromReferrer(referrer: string | null): string | null {
  if (!referrer) return null;
  try {
    return new URL(referrer).hostname.toLowerCase();
  } catch {
    return null;
  }
}


function hostMatchesDomain(host: string, domain: string): boolean {
  const h = host.toLowerCase().replace(/\.+$/, "");
  const d = domain.toLowerCase();
  return h === d || h.endsWith(`.${d}`);
}

function isGoogleHost(host: string): boolean {
  if (hostMatchesDomain(host, "google.com")) return true;
  const parts = host.toLowerCase().split(".");
  return parts.length >= 2 && parts[parts.length - 2] === "google";
}

const RECOGNIZED_UTM: Record<string, AcquisitionTouch["source"]> = {
  torob: "torob",
  trob: "torob",
  emalls: "emalls",
  emall: "emalls",
  instagram: "instagram",
  ig: "instagram",
  google: "google",
  google_ads: "google",
  adwords: "google",
};

function googleSubtype(utmMedium: string | null, utmSource: string | null): string {
  const medium = (utmMedium || "").toLowerCase();
  const source = (utmSource || "").toLowerCase();
  if (["cpc", "ppc", "paid", "paidsearch"].includes(medium)) return "google_paid";
  if (source.startsWith("google") && ["cpc", "ppc", "paid"].includes(medium)) return "google_paid";
  if (medium === "organic" || medium === "search") return "google_organic";
  return "google_unspecified";
}

export function classifyVisit(input: {
  landingPath: string;
  referrer: string | null;
  utmSource: string | null;
  utmMedium: string | null;
  utmCampaign: string | null;
  capturedAt: string;
}): AcquisitionTouch {
  const path = input.landingPath.slice(0, 256);
  const utmS = (input.utmSource || "").trim().toLowerCase();
  const utmM = (input.utmMedium || "").trim().toLowerCase();
  const utmC = (input.utmCampaign || "").trim();
  const host = hostFromReferrer(input.referrer);
  const campaign =
    utmS || utmM || utmC
      ? { utm_source: utmS || null, utm_medium: utmM || null, utm_campaign: utmC || null }
      : null;

  const recognized = RECOGNIZED_UTM[utmS];
  if (recognized) {
    const subtype = recognized === "google" ? googleSubtype(utmM, utmS) : undefined;
    return {
      source: recognized,
      source_subtype: subtype,
      method: "utm",
      landing_path: path,
      campaign,
      captured_at: input.capturedAt,
    };
  }

  if (host) {
    if (hostMatchesDomain(host, "torob.com"))
      return { source: "torob", method: "referrer", landing_path: path, campaign: null, captured_at: input.capturedAt };
    if (hostMatchesDomain(host, "emalls.ir"))
      return { source: "emalls", method: "referrer", landing_path: path, campaign: null, captured_at: input.capturedAt };
    if (hostMatchesDomain(host, "instagram.com") || hostMatchesDomain(host, "l.instagram.com"))
      return { source: "instagram", method: "referrer", landing_path: path, campaign: null, captured_at: input.capturedAt };
    if (isGoogleHost(host))
      return {
        source: "google",
        source_subtype: "google_unspecified",
        method: "referrer",
        landing_path: path,
        campaign: null,
        captured_at: input.capturedAt,
      };
  }

  if (utmS)
    return { source: "other", method: "utm", landing_path: path, campaign, captured_at: input.capturedAt };
  if (host)
    return { source: "other", method: "referrer", landing_path: path, campaign: null, captured_at: input.capturedAt };
  return { source: "direct", method: "direct", landing_path: path, campaign: null, captured_at: input.capturedAt };
}


export function mergeState(existing: AttributionState | null, visit: AcquisitionTouch): AttributionState {
  const state: AttributionState = {
    first_touch: existing?.first_touch ?? null,
    last_non_direct_touch: existing?.last_non_direct_touch ?? null,
  };
  if (!state.first_touch) state.first_touch = visit;
  if (visit.source !== "direct") state.last_non_direct_touch = visit;
  return state;
}
