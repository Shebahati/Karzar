"use client";

import { useEffect, useState } from "react";

/** True when desktop (≥1024px) and user has not requested reduced motion — skip heavy animations on mobile. */
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

/** True below the `md` breakpoint (phone / small tablet portrait). */
export function useIsMobileMd(): boolean {
  const [mobile, setMobile] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    const update = () => setMobile(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);

  return mobile;
}

/**
 * True when fine-pointer hover is available — skip hover-swap dual images
 * and hover-only chrome on touch devices.
 */
export function useCanHover(): boolean {
  const [canHover, setCanHover] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(hover: hover) and (pointer: fine)");
    const update = () => setCanHover(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);

  return canHover;
}
