"use client";

import { useEffect, useState } from "react";

/** True on desktop when user has not requested reduced motion — use to skip heavy animations on mobile. */
export function useMotionSafe(): boolean {
  const [enabled, setEnabled] = useState(false);

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    const mobile = window.matchMedia("(max-width: 1023px)");

    const update = () => {
      setEnabled(!reduced.matches && !mobile.matches);
    };

    update();
    reduced.addEventListener("change", update);
    mobile.addEventListener("change", update);
    return () => {
      reduced.removeEventListener("change", update);
      mobile.removeEventListener("change", update);
    };
  }, []);

  return enabled;
}
