"use client";

import { useEffect } from "react";
import { captureAttributionFromWindow } from "./storage";

export function AttributionCapture() {
  useEffect(() => {
    captureAttributionFromWindow();
  }, []);
  return null;
}
