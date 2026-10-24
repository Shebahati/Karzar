export const ATTRIBUTION_COOKIE = "karzar_attribution_v1";
export const ATTRIBUTION_MAX_AGE_DAYS = 30;

export const ACQUISITION_SOURCES = [
  "torob",
  "emalls",
  "instagram",
  "google",
  "direct",
  "other",
  "unknown",
] as const;

export type AcquisitionSource = (typeof ACQUISITION_SOURCES)[number];
