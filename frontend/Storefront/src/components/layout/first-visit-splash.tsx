"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

/** sessionStorage — first load per tab/session; refresh/nav within session skips. */
export const SPLASH_STORAGE_KEY = "karzar-splash-seen";

/** Head boot injects `<style data-karzar-splash-boot>` for FOUC (not an html attr). */
const SPLASH_BOOT_STYLE = "style[data-karzar-splash-boot]";

const MIN_DWELL_MS = 1000;
const MAX_WAIT_MS = 2200;
const FADE_OUT_MS = 480;

const MIN_DWELL_REDUCED_MS = 180;
const MAX_WAIT_REDUCED_MS = 400;
const FADE_OUT_REDUCED_MS = 160;

type Phase = "boot" | "show" | "exit" | "done";

function removeBootStyle() {
  document.querySelector(SPLASH_BOOT_STYLE)?.remove();
}

/** Defensive: clear any leftover attr from older splash builds (avoids stuck CSS veil). */
function clearLegacySplashAttr() {
  document.documentElement.removeAttribute("data-karzar-splash");
}

/**
 * Soft first-visit splash — fully React-owned overlay.
 *
 * Head boot script injects a FOUC `<style>` only (never mutates `html` attrs React
 * owns). Scroll lock is applied via inline overflow styles — never `data-karzar-splash`
 * on `<html>`, so hydrate cannot mismatch and a leftover attr cannot pin a permanent veil.
 * Boot style stays until dismiss so cover never drops between boot → React overlay.
 */
export function FirstVisitSplash() {
  const [phase, setPhase] = useState<Phase>("boot");
  const [ready, setReady] = useState(false);
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    const html = document.documentElement;
    const body = document.body;
    const prevHtmlOverflow = html.style.overflow;
    const prevBodyOverflow = body.style.overflow;

    let alreadySeen = false;
    try {
      alreadySeen = sessionStorage.getItem(SPLASH_STORAGE_KEY) === "1";
    } catch {
      /* private mode — still attempt splash once */
    }

    clearLegacySplashAttr();

    if (alreadySeen) {
      removeBootStyle();
      setPhase("done");
      return;
    }

    // Keep boot style until dismiss — React overlay stacks on top; no html attr veil.
    html.style.overflow = "hidden";
    body.style.overflow = "hidden";
    setReduced(window.matchMedia("(prefers-reduced-motion: reduce)").matches);
    setPhase("show");

    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const isMobile = window.matchMedia("(max-width: 767px)").matches;

    // Shorter dwell on phones so splash doesn't feel like a block.
    const minDwell = prefersReduced
      ? MIN_DWELL_REDUCED_MS
      : isMobile
        ? 650
        : MIN_DWELL_MS;
    const maxWait = prefersReduced
      ? MAX_WAIT_REDUCED_MS
      : isMobile
        ? 1600
        : MAX_WAIT_MS;
    const fadeOut = prefersReduced ? FADE_OUT_REDUCED_MS : isMobile ? 320 : FADE_OUT_MS;

    const enterRaf = requestAnimationFrame(() => {
      setReady(true);
    });

    const started = performance.now();
    let loadReady = document.readyState === "complete";
    let dismissed = false;
    let exitTimer: number | undefined;
    let dwellTimer: number | undefined;

    const restoreScroll = () => {
      html.style.overflow = prevHtmlOverflow;
      body.style.overflow = prevBodyOverflow;
    };

    const markSeen = () => {
      try {
        sessionStorage.setItem(SPLASH_STORAGE_KEY, "1");
      } catch {
        /* private mode / blocked storage — still dismiss once */
      }
    };

    const dismiss = () => {
      if (dismissed) return;
      dismissed = true;
      markSeen();
      clearLegacySplashAttr();
      removeBootStyle();
      restoreScroll();
      setPhase("exit");
      exitTimer = window.setTimeout(() => {
        setPhase("done");
      }, fadeOut);
    };

    const tryDismiss = () => {
      if (dismissed) return;
      const elapsed = performance.now() - started;
      const canExit = loadReady || elapsed >= maxWait;
      if (!canExit) return;
      const wait = Math.max(0, minDwell - elapsed);
      if (dwellTimer !== undefined) window.clearTimeout(dwellTimer);
      dwellTimer = window.setTimeout(dismiss, wait);
    };

    const onLoad = () => {
      loadReady = true;
      tryDismiss();
    };

    if (loadReady) {
      tryDismiss();
    } else {
      window.addEventListener("load", onLoad, { once: true });
    }

    const maxTimer = window.setTimeout(() => {
      loadReady = true;
      tryDismiss();
    }, maxWait);

    return () => {
      cancelAnimationFrame(enterRaf);
      window.clearTimeout(maxTimer);
      if (dwellTimer !== undefined) window.clearTimeout(dwellTimer);
      if (exitTimer !== undefined) window.clearTimeout(exitTimer);
      window.removeEventListener("load", onLoad);
      clearLegacySplashAttr();
      removeBootStyle();
      restoreScroll();
    };
  }, []);

  if (phase === "boot" || phase === "done") return null;

  return (
    <div
      className={cn(
        "karzar-splash",
        reduced ? "karzar-splash--reduced" : "karzar-splash--animate",
        ready && "karzar-splash--ready",
        phase === "exit" && "karzar-splash--exit",
      )}
      role="status"
      aria-live="polite"
      aria-busy={phase !== "exit"}
      aria-label="کارزار"
      style={phase === "exit" ? { pointerEvents: "none" } : undefined}
    >
      <div className="karzar-splash__veil" aria-hidden="true" />
      <div className="karzar-splash__inner">
        {/* eslint-disable-next-line @next/next/no-img-element -- splash paints before next/image */}
        <img
          className="karzar-splash__logo"
          src="/images/brand/logo.svg"
          alt=""
          width={240}
          height={38}
          decoding="async"
          fetchPriority="high"
        />
        <span className="karzar-splash__accent" aria-hidden="true" />
        <span className="karzar-splash__hairline" aria-hidden="true" />
      </div>
    </div>
  );
}
