"use client";

import { campaignMediaForSlide } from "@/lib/hero-campaign-layout";
import { cn } from "@/lib/utils";
import type { DesignedHeroSlide } from "@/types/hero-design";

/**
 * Reserves compact campaign hero height without loading images.
 * Used in the mobile strip grid shell so all five slides share one max stage.
 */
export function CampaignHeroGeometrySizer({ slide }: { slide: DesignedHeroSlide }) {
  const media = campaignMediaForSlide(slide.id);
  const { typography: t, buttons } = slide.config;

  return (
    <div
      data-testid="campaign-hero-geometry-sizer"
      data-slide-id={slide.id}
      data-cta-count={buttons.length}
      className="flex w-full flex-col overflow-hidden bg-[#121212]"
    >
      <div
        className="w-full shrink-0"
        style={{ aspectRatio: `${media.compactAspect}` }}
        data-testid="campaign-geometry-media-band"
        aria-hidden
      />
      <div className={cn("flex flex-col bg-[#121212]", media.compactCopyClass)}>
        <div
          className={cn(
            "font-extrabold leading-[1.2] tracking-tight",
            "text-[clamp(1.35rem,5.2vw,1.65rem)]",
          )}
          style={{ color: t.titleColor }}
        >
          {t.title}
        </div>
        <div className="mt-2 h-px w-10 bg-[rgba(208,35,39,0.85)]" aria-hidden />
        <p
          className="mt-2 w-full text-sm font-normal leading-relaxed sm:text-[15px]"
          style={{ color: t.subtitleColor }}
        >
          {t.subtitle}
        </p>
        {buttons.length ? (
          <div
            className="mt-3 flex w-full flex-wrap items-center justify-start gap-2.5"
            data-testid="campaign-geometry-cta-row"
          >
            {buttons.map((button) => (
              <span
                key={button.id}
                data-testid="campaign-geometry-cta-slot"
                className="inline-flex min-h-[44px] items-center justify-center rounded-xl px-5 py-2.5 text-sm font-semibold"
                aria-hidden
              >
                {button.label}
              </span>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}
