"use client";

import Link from "next/link";
import type { CSSProperties } from "react";
import {
  CAMPAIGN_MOBILE_SOURCE_MAX_PX,
  campaignDesktopImageUrl,
  campaignMediaForSlide,
} from "@/lib/hero-campaign-layout";
import { HeroImageHandoff } from "@/lib/hero-image-handoff";
import { cn } from "@/lib/utils";
import type { DesignedHeroSlide } from "@/types/hero-design";

function overlayCss(slide: DesignedHeroSlide): string {
  const o = slide.config.overlay;
  if (o.mode === "solid") return o.solidColor;
  return `linear-gradient(${o.gradientAngle}deg, ${o.gradientFrom}, ${o.gradientTo})`;
}

function HeroCopyStack({
  slide,
  primaryHeading,
  compact,
  visible,
}: {
  slide: DesignedHeroSlide;
  primaryHeading?: boolean;
  compact: boolean;
  visible: boolean;
}) {
  const { typography: t, buttons } = slide.config;
  const TitleTag = primaryHeading ? "h1" : "h2";

  return (
    <div
      className={cn(
        "flex flex-col text-right transition-opacity duration-300",
        !visible && "pointer-events-none opacity-0",
        visible && "opacity-100",
      )}
      aria-hidden={!visible}
    >
      <TitleTag
        className={cn(
          "font-extrabold leading-[1.2] tracking-tight drop-shadow-[0_2px_18px_rgba(0,0,0,0.45)]",
          compact ? "text-[clamp(1.35rem,5.2vw,1.65rem)]" : "text-[clamp(1.75rem,2.4vw,2.75rem)]",
        )}
        style={{ color: t.titleColor }}
      >
        {t.title}
      </TitleTag>
      <div className="mt-3 h-px w-10 bg-[rgba(208,35,39,0.85)]" aria-hidden />
      <p
        className={cn(
          "mt-3 max-w-prose font-normal leading-relaxed",
          compact
            ? "text-sm leading-relaxed sm:text-[15px]"
            : "text-[clamp(0.95rem,1.1vw,1.0625rem)] drop-shadow-[0_1px_12px_rgba(0,0,0,0.4)]",
        )}
        style={{ color: t.subtitleColor }}
      >
        {t.subtitle}
      </p>
      {buttons.length ? (
        <div
          className={cn(
            "mt-5 flex flex-wrap items-center justify-start gap-3",
            compact ? "mt-4" : "mt-6",
          )}
        >
          {buttons.map((button) => {
            const href = button.action.type === "href" ? button.action.value : "/catalog";
            const preset =
              button.stylePreset ?? (button.variant === "glass" ? "on-dark-glass" : "primary");
            const visual: CSSProperties =
              preset === "soft"
                ? { background: "#5E5F5E", color: "#fff" }
                : { background: "#D02327", color: "#fff" };
            return (
              <Link
                key={button.id}
                href={href}
                className={cn(
                  "inline-flex min-h-11 items-center justify-center rounded-xl px-5 py-2.5 text-sm font-semibold",
                  "transition hover:opacity-95 active:scale-[0.98]",
                  compact && "min-h-[44px] sm:w-auto",
                )}
                style={visual}
              >
                {button.label}
              </Link>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

/** Full-bleed five-hero slide: image covers stage, RTL copy and CTAs overlay the image. */
export function CampaignHeroSlide({
  slide,
  compact,
  priority,
  primaryHeading,
  contentVisible = true,
  onImageReadyChange,
  className,
}: {
  slide: DesignedHeroSlide;
  compact: boolean;
  priority?: boolean;
  primaryHeading?: boolean;
  contentVisible?: boolean;
  onImageReadyChange?: (ready: boolean) => void;
  className?: string;
}) {
  const media = campaignMediaForSlide(slide.id);
  const imageUrl = campaignDesktopImageUrl(slide);
  const focal = compact ? media.mobileFocal : media.desktopFocal;
  const overlayOpacity = slide.config.overlay.opacity;
  const mobileSrc = slide.config.background.mobileImageUrl;

  if (compact) {
    return (
      <div
        className={cn("relative flex h-full w-full flex-col overflow-hidden bg-[#121212]", className)}
        data-testid="campaign-hero-compact"
      >
        <div
          className="relative w-full shrink-0 overflow-hidden"
          style={{ aspectRatio: `${media.compactAspect}` }}
          data-testid="campaign-hero-compact-media"
        >
          <HeroImageHandoff
            key={slide.id}
            slideKey={slide.id}
            desktopSrc={imageUrl}
            mobileSrc={mobileSrc}
            focal={focal}
            priority={priority}
            mobileSourceMaxWidthPx={CAMPAIGN_MOBILE_SOURCE_MAX_PX}
            onReadyChange={onImageReadyChange}
            className="absolute inset-0 h-full w-full"
            imageClassName="object-cover"
          />
          <div
            className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_top,rgba(0,0,0,0.55)_0%,transparent_55%)]"
            aria-hidden
          />
        </div>
        <div className={cn("relative z-10 flex flex-col bg-[#121212]", media.compactCopyClass)}>
          <HeroCopyStack
            slide={slide}
            compact
            primaryHeading={primaryHeading}
            visible={contentVisible}
          />
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn("relative h-full w-full overflow-hidden", className)}
      data-testid="campaign-hero-fullbleed"
    >
      <HeroImageHandoff
        key={slide.id}
        slideKey={slide.id}
        desktopSrc={imageUrl}
        mobileSrc={mobileSrc}
        focal={focal}
        priority={priority}
        onReadyChange={onImageReadyChange}
        className="absolute inset-0 h-full w-full"
        imageClassName="object-cover"
      />

      {/* RTL-weighted readability: darker toward the right (copy side), subtle bottom for dock */}
      <div
        className="pointer-events-none absolute inset-0 bg-[linear-gradient(270deg,rgba(0,0,0,0.72)_0%,rgba(0,0,0,0.38)_38%,transparent_68%)]"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_top,rgba(0,0,0,0.5)_0%,transparent_42%)]"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute inset-0"
        style={{ background: overlayCss(slide), opacity: overlayOpacity * 0.22 }}
        aria-hidden
      />

      <div
        className={cn(
          "absolute z-20 flex flex-col text-right",
          media.desktopCopyClass,
        )}
      >
        <HeroCopyStack
          slide={slide}
          compact={false}
          primaryHeading={primaryHeading}
          visible={contentVisible}
        />
      </div>
    </div>
  );
}
