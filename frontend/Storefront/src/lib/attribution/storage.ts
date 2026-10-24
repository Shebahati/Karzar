import { ATTRIBUTION_COOKIE, ATTRIBUTION_MAX_AGE_DAYS } from "./constants";
import type { AcquisitionTouch, AttributionState } from "./types";
import { classifyVisit, mergeState } from "./resolver";

const MAX_AGE_MS = ATTRIBUTION_MAX_AGE_DAYS * 24 * 60 * 60 * 1000;

function readCookie(): AttributionState | null {
  if (typeof document === "undefined") return null;
  const raw = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${ATTRIBUTION_COOKIE}=`))
    ?.split("=")[1];
  if (!raw) return null;
  try {
    return JSON.parse(decodeURIComponent(raw)) as AttributionState;
  } catch {
    return null;
  }
}

function writeCookie(state: AttributionState) {
  const encoded = encodeURIComponent(JSON.stringify(state));
  const maxAge = Math.floor(MAX_AGE_MS / 1000);
  document.cookie = `${ATTRIBUTION_COOKIE}=${encoded}; path=/; max-age=${maxAge}; SameSite=Lax`;
}

export function captureAttributionFromWindow() {
  if (typeof window === "undefined") return;
  const params = new URLSearchParams(window.location.search);
  const visit = classifyVisit({
    landingPath: window.location.pathname,
    referrer: document.referrer || null,
    utmSource: params.get("utm_source"),
    utmMedium: params.get("utm_medium"),
    utmCampaign: params.get("utm_campaign"),
    capturedAt: new Date().toISOString(),
  });
  const merged = mergeState(readCookie(), visit);
  writeCookie(merged);
}

export function getAttributionCheckoutSnapshot() {
  const state = readCookie();
  if (!state) return null;
  return {
    first_touch: state.first_touch,
    last_non_direct_touch: state.last_non_direct_touch,
  };
}
