"use client";

import Link from "next/link";
import type { CSSProperties, ReactNode } from "react";
import {
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
          "font-extrabold leading-[1.2] tracking-tight",
          compact ? "text-[clamp(1.35rem,5.2vw,1.65rem)]" : "text-[clamp(1.75rem,2.4vw,2.75rem)]",
        )}
        style={{ color: t.titleColor }}
      >
        {t.title}
      </TitleTag>
      <div
        className="mt-3 h-px w-10 bg-[rgba(208,35,39,0.85)]"
        aria-hidden
      />
      <p
        className={cn(
          "mt-3 max-w-prose font-normal leading-relaxed",
          compact ? "text-sm sm:text-[15px]" : "text-[clamp(0.95rem,1.1vw,1.0625rem)]",
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
                  compact && "min-h-[44px] w-full sm:w-auto",
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
  const focal = compact ? media.compactFocal : media.desktopFocal;
  const overlayOpacity = slide.config.overlay.opacity;

  if (compact) {
    return (
      <div
        className={cn("flex h-full w-full flex-col bg-[#1a1a1a]", className)}
        data-testid="campaign-hero-compact"
      >
        <div
          className="relative w-full shrink-0 overflow-hidden bg-[#121212]"
          style={{ aspectRatio: `${media.compactAspect}` }}
        >
          <HeroImageHandoff
            key={slide.id}
            slideKey={slide.id}
            desktopSrc={imageUrl}
            mobileSrc={slide.config.background.mobileImageUrl}
            focal={focal}
            priority={priority}
            compactMedia
            onReadyChange={onImageReadyChange}
            imageClassName="object-cover"
          />
          <div
            className="pointer-events-none absolute inset-0"
            style={{ background: overlayCss(slide), opacity: overlayOpacity * 0.35 }}
          />
        </div>
        <div className="flex flex-1 flex-col px-[clamp(1rem,4.5vw,1.25rem)] py-4 pb-5">
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
      className={cn(
        "relative grid h-full w-full grid-cols-1 bg-[#1a1a1a] lg:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]",
        className,
      )}
      data-testid="campaign-hero-desktop"
    >
      <div className="relative min-h-[240px] overflow-hidden lg:min-h-0">
        <HeroImageHandoff
          slideKey={slide.id}
          desktopSrc={imageUrl}
          mobileSrc={slide.config.background.mobileImageUrl}
          focal={focal}
          priority={priority}
          onReadyChange={onImageReadyChange}
          imageClassName="object-cover"
        />
        <div
          className="pointer-events-none absolute inset-0 lg:hidden"
          style={{ background: overlayCss(slide), opacity: overlayOpacity * 0.25 }}
        />
      </div>
      <div className="relative flex items-center px-6 py-8 lg:px-10 lg:py-10">
        <div
          className="pointer-events-none absolute inset-0 hidden lg:block"
          style={{
            background:
              "linear-gradient(105deg, rgba(8,8,8,0.08) 0%, rgba(12,12,12,0.55) 38%, rgba(18,18,18,0.92) 100%)",
          }}
        />
        <div className="relative z-10 w-full max-w-[460px] lg:ms-auto">
          <HeroCopyStack
            slide={slide}
            compact={false}
            primaryHeading={primaryHeading}
            visible={contentVisible}
          />
        </div>
      </div>
    </div>
  );
}

export function CampaignHeroSlideLayer({
  children,
}: {
  children: ReactNode;
}) {
  return <div className="absolute inset-0">{children}</div>;
}
