/** Feature labels — API-first with local fallback (decision 12-A). */

"use client";

import { useEffect, useSyncExternalStore } from "react";
import { catalogService } from "@/services/catalog";

const FALLBACK_LABELS: Record<string, string> = {
  waterproof: "ضدآب (IP)",
  data_output: "خروجی داده",
  auto_power_off: "خاموش شدن خودکار",
  has_buttons: "دارای دکمه",
  buttons_list: "دکمه‌ها",
  grade: "گرید",
  coating: "پوشش",
  geometry: "ژئومتری",
  insert_shape: "شکل اینسرت",
  corner_radius_mm: "شعاع گوشه (mm)",
  material: "جنس",
  standard: "استاندارد",
  range: "بازه اندازه‌گیری",
  accuracy: "دقت",
  resolution: "رزولوشن",
  battery_type: "نوع باتری",
  diameter_mm: "قطر (mm)",
  flutes: "تعداد تیغه",
  helix_angle: "زاویه مارپیچ",
  length_of_cut_mm: "طول برش (mm)",
  point_angle: "زاویه نوک",
  flute_length_mm: "طول شیار (mm)",
  is_original: "اورجینال",
  has_certification: "دارای گواهی",
  coolant_through: "آبسردکن داخلی",
  certification_text: "متن گواهی",
};

let cachedLabels: Record<string, string> | null = null;
let inflight: Promise<Record<string, string>> | null = null;
let version = 0;
const listeners = new Set<() => void>();

function notifyLabelsChanged() {
  version += 1;
  listeners.forEach((listener) => listener());
}

function subscribeLabels(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getLabelsVersion() {
  return version;
}

export function getFeatureLabelSync(key: string): string {
  return cachedLabels?.[key] ?? FALLBACK_LABELS[key] ?? key;
}

export async function loadFeatureLabels(): Promise<Record<string, string>> {
  if (cachedLabels) return cachedLabels;
  if (inflight) return inflight;

  inflight = catalogService
    .getSpecLabels()
    .then((labels) => {
      cachedLabels = { ...FALLBACK_LABELS, ...labels };
      notifyLabelsChanged();
      return cachedLabels;
    })
    .catch(() => {
      cachedLabels = { ...FALLBACK_LABELS };
      notifyLabelsChanged();
      return cachedLabels;
    })
    .finally(() => {
      inflight = null;
    });

  return inflight;
}

export function getFeatureLabel(key: string): string {
  return getFeatureLabelSync(key);
}

/** Subscribe so filter chips/panels re-render after labels load from API. */
export function useFeatureLabel(key: string): string {
  useSyncExternalStore(subscribeLabels, getLabelsVersion, getLabelsVersion);

  useEffect(() => {
    void loadFeatureLabels();
  }, []);

  return getFeatureLabelSync(key);
}
