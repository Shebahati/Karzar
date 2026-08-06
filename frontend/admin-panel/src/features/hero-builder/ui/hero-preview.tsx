"use client";

import { useRef, type CSSProperties, type PointerEvent as REPointerEvent } from "react";
import * as Icons from "react-iconly";
import { Category as CategoryIcon } from "react-iconly";
import { cn } from "@/lib/utils";
import {
  buttonSizeCss,
  buttonStyleCss,
  composeHeroForMobile,
  type HeroBuilderConfig,
  type HeroButton,
  type MobileComposePreset,
} from "@/entities/hero";
import { HeroBadgeView } from "./hero-badge-view";

function overlayCss(config: HeroBuilderConfig): string {
  const o = config.overlay;
  if (o.mode === "solid") return o.solidColor;
  return `linear-gradient(${o.gradientAngle}deg, ${o.gradientFrom}, ${o.gradientTo})`;
}

function DockIcon({ name, size = 14 }: { name: string; size?: number }) {
  const Cmp = (Icons as Record<string, unknown>)[name] as
    | React.ComponentType<{
        size?: number | string;
        set?: string;
        primaryColor?: string;
        stroke?: string;
      }>
    | undefined;
  if (!Cmp) {
    return <CategoryIcon size={size} set="light" primaryColor="#fff" stroke="light" />;
  }
  return <Cmp size={size} set="light" primaryColor="#fff" stroke="light" />;
}

function pointerToLogicalPercent(
  clientX: number,
  clientY: number,
  rect: DOMRect,
  rtl: boolean,
): { x: number; y: number } {
  // X = distance from inline-start (right edge in RTL), matching insetInlineStart.
  const x = rtl
    ? ((rect.right - clientX) / rect.width) * 100
    : ((clientX - rect.left) / rect.width) * 100;
  const y = ((clientY - rect.top) / rect.height) * 100;
  return { x, y };
}

function Draggable({
  x,
  y,
  selected,
  onSelect,
  onMove,
  className,
  style,
  children,
}: {
  x: number;
  y: number;
  selected?: boolean;
  onSelect?: () => void;
  onMove?: (pos: { x: number; y: number }) => void;
  className?: string;
  style?: CSSProperties;
  children: React.ReactNode;
}) {
  const dragging = useRef(false);
  /** Pointer offset from layer origin in logical % (inline-start / top). */
  const grab = useRef<{ ox: number; oy: number } | null>(null);
  const stageRef = useRef<HTMLElement | null>(null);
  const rtlRef = useRef(false);

  const onPointerDown = (e: REPointerEvent<HTMLDivElement>) => {
    e.stopPropagation();
    onSelect?.();
    if (!onMove) return;
    dragging.current = true;
    const stage = e.currentTarget.closest("[data-hero-stage]") as HTMLElement | null;
    stageRef.current = stage;
    rtlRef.current = stage
      ? getComputedStyle(stage).direction === "rtl"
      : document.documentElement.dir === "rtl";
    if (stage) {
      const rect = stage.getBoundingClientRect();
      const p = pointerToLogicalPercent(e.clientX, e.clientY, rect, rtlRef.current);
      grab.current = { ox: p.x - x, oy: p.y - y };
    } else {
      grab.current = { ox: 0, oy: 0 };
    }
    e.currentTarget.setPointerCapture(e.pointerId);
  };

  const onPointerMove = (e: REPointerEvent<HTMLDivElement>) => {
    if (!dragging.current || !grab.current || !onMove) return;
    const stage = stageRef.current;
    if (!stage) return;
    const rect = stage.getBoundingClientRect();
    const p = pointerToLogicalPercent(e.clientX, e.clientY, rect, rtlRef.current);
    onMove({
      x: Math.min(100, Math.max(0, p.x - grab.current.ox)),
      y: Math.min(100, Math.max(0, p.y - grab.current.oy)),
    });
  };

  const onPointerUp = () => {
    dragging.current = false;
    grab.current = null;
  };

  return (
    <div
      role="button"
      tabIndex={0}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      className={cn(
        "absolute z-20 touch-none select-none",
        onMove && "cursor-grab active:cursor-grabbing",
        selected && "z-30 ring-2 ring-white ring-offset-2 ring-offset-black/20",
        className,
      )}
      style={{ insetInlineStart: `${x}%`, top: `${y}%`, ...style }}
    >
      {children}
      {selected ? (
        <span className="pointer-events-none absolute -inset-1 rounded-xl border border-dashed border-white/70" />
      ) : null}
    </div>
  );
}

function ButtonView({ button }: { button: HeroButton }) {
  const style = buttonStyleCss(button.stylePreset ?? "primary");
  const size = buttonSizeCss(button.sizePreset ?? "md");
  const styleBase: CSSProperties = {
    borderRadius: size.borderRadius,
    padding: size.padding,
    fontSize: size.fontSize,
    color: style.color,
    background: style.background,
    border: style.border,
    backdropFilter: style.backdropFilter,
  };

  return (
    <div className="font-bold whitespace-nowrap shadow-[0_8px_24px_rgba(0,0,0,0.22)]" style={styleBase}>
      {button.label}
    </div>
  );
}

export function HeroPreview({
  config,
  selectedLayerId,
  showGrid,
  gridSize,
  featuredOrbs = [],
  activeOrbIndex = 0,
  onSelectOrb,
  lockDrag = false,
  mobilePreset = null,
  onSelectLayer,
  onMoveLayer,
  className,
}: {
  config: HeroBuilderConfig;
  selectedLayerId?: string | null;
  showGrid?: boolean;
  gridSize?: number;
  featuredOrbs?: Array<{ key: string; name: string; icon: string }>;
  activeOrbIndex?: number;
  onSelectOrb?: (orbKey: string) => void;
  lockDrag?: boolean;
  /** When set, layout is remapped into a distinct mobile composition */
  mobilePreset?: MobileComposePreset | null;
  onSelectLayer?: (id: string) => void;
  onMoveLayer?: (
    kind: "typography" | "button" | "badge" | "carousel",
    id: string | null,
    pos: { x: number; y: number },
  ) => void;
  className?: string;
}) {
  const mobile = mobilePreset ? composeHeroForMobile(config, mobilePreset) : null;
  const cfg = mobile?.config ?? config;
  const overlayOpacity = mobile?.overlayOpacity ?? cfg.overlay.opacity;

  const animClass = cfg.animation === "none" ? "" : `hero-anim-${cfg.animation}`;

  const move = lockDrag || mobilePreset ? undefined : onMoveLayer;

  const gridBg =
    showGrid && gridSize
      ? {
          backgroundImage: `
            linear-gradient(to right, rgba(255,255,255,0.08) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(255,255,255,0.08) 1px, transparent 1px)
          `,
          backgroundSize: `${gridSize}% ${gridSize}%`,
        }
      : undefined;

  return (
    <div
      data-hero-stage
      dir="rtl"
      className={cn(
        "relative h-full w-full overflow-hidden rounded-2xl bg-[#111] shadow-elevated",
        className,
      )}
    >
      <div className="absolute inset-0 overflow-hidden">
        {cfg.background.mode === "color" ? (
          <div className="h-full w-full" style={{ background: cfg.background.color }} />
        ) : (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={cfg.background.imageUrl || "/images/hero/karzar-metrology-lab.jpg"}
            alt=""
            className="absolute inset-0 h-full w-full object-cover"
            style={{ objectPosition: cfg.background.focal || "center" }}
            draggable={false}
          />
        )}
      </div>

      <div
        className="absolute inset-0"
        style={{ background: overlayCss(cfg), opacity: overlayOpacity }}
      />

      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_80%_0%,rgba(208,35,39,0.2),transparent_42%)]"
      />

      {showGrid ? (
        <div className="pointer-events-none absolute inset-0 z-[5]" style={gridBg} />
      ) : null}

      {mobilePreset ? (
        <div className="pointer-events-none absolute inset-x-0 top-0 z-50 flex flex-col gap-1 p-3">
          <div className="w-fit rounded-lg bg-black/45 px-2 py-1 text-[9px] font-bold text-white/90 backdrop-blur-sm">
            موبایل · {mobile?.label}
          </div>
          <div className="w-fit max-w-[90%] rounded-lg bg-black/40 px-2 py-1 text-[8px] font-medium leading-snug text-white/75 backdrop-blur-sm">
            داک داخل هیرو نیست — دسته‌ها بخش جدا زیر هیرو
          </div>
        </div>
      ) : null}

      <div className={cn("absolute inset-0", animClass)}>
        <Draggable
          x={cfg.typography.position.x}
          y={cfg.typography.position.y}
          selected={selectedLayerId === "typography"}
          onSelect={() => onSelectLayer?.("typography")}
          onMove={(pos) => move?.("typography", null, pos)}
          style={{
            width: `min(${cfg.typography.maxWidth}px, 92%)`,
            maxWidth: "92%",
            textAlign:
              cfg.typography.align === "start"
                ? "right"
                : cfg.typography.align === "end"
                  ? "left"
                  : "center",
          }}
          className={cn(cfg.animation === "stagger-up" && "hero-stagger-1")}
        >
          <h2
            className="font-black leading-[1.15] tracking-tight drop-shadow-[0_2px_12px_rgba(0,0,0,0.55)]"
            style={{
              color: cfg.typography.titleColor,
              fontSize: `clamp(1.15rem, 3.2vw, ${cfg.typography.titleSize}px)`,
            }}
          >
            {cfg.typography.title || "عنوان هیرو"}
          </h2>
          <div className="mt-2 h-1 w-12 rounded-full bg-primary" />
          <p
            className="mt-3 font-medium leading-relaxed drop-shadow-[0_1px_8px_rgba(0,0,0,0.5)]"
            style={{ color: cfg.typography.subtitleColor, fontSize: cfg.typography.subtitleSize }}
          >
            {cfg.typography.subtitle}
          </p>
        </Draggable>

        {cfg.buttons.map((button, i) => (
          <Draggable
            key={button.id}
            x={button.position.x}
            y={button.position.y}
            selected={selectedLayerId === button.id}
            onSelect={() => onSelectLayer?.(button.id)}
            onMove={(pos) => move?.("button", button.id, pos)}
            className={cn(cfg.animation === "stagger-up" && `hero-stagger-${Math.min(i + 2, 4)}`)}
          >
            <ButtonView button={button} />
          </Draggable>
        ))}

        {cfg.badges.map((badge) => (
          <Draggable
            key={badge.id}
            x={badge.position.x}
            y={badge.position.y}
            selected={selectedLayerId === badge.id}
            onSelect={() => onSelectLayer?.(badge.id)}
            onMove={(pos) => move?.("badge", badge.id, pos)}
          >
            <div className="relative">
              <HeroBadgeView badge={badge} inline />
            </div>
          </Draggable>
        ))}

        {cfg.carousel.enabled ? (
          <Draggable
            x={cfg.carousel.position.x}
            y={cfg.carousel.position.y}
            selected={selectedLayerId === "carousel"}
            onSelect={() => onSelectLayer?.("carousel")}
            onMove={(pos) => move?.("carousel", null, pos)}
            className={cn(
              "w-[min(340px,46%)]",
              cfg.carousel.layoutPreset === "row-large" && "w-[min(420px,58%)]",
              cfg.carousel.layoutPreset === "row-compact" && "w-[min(280px,40%)]",
              cfg.carousel.layoutPreset === "stack" && "w-[min(220px,42%)]",
              cfg.animation === "stagger-up" && "hero-stagger-4",
            )}
          >
            <div
              className={cn(
                "rounded-2xl p-3 shadow-[0_12px_36px_rgba(0,0,0,0.28)]",
                (cfg.carousel.stylePreset ?? "rail-soft") === "cards-elevated" &&
                  "bg-white text-ink",
                (cfg.carousel.stylePreset ?? "rail-soft") === "rail-soft" &&
                  "bg-white/14 text-white",
                (cfg.carousel.stylePreset ?? "rail-soft") === "strip-minimal" &&
                  "bg-transparent text-white",
                (cfg.carousel.stylePreset ?? "rail-soft") === "spotlight" &&
                  "bg-white/18 text-white",
              )}
            >
              <div className="mb-2 flex items-center justify-between gap-2">
                <span className="text-xs font-bold">
                  {cfg.carousel.categoryLabel || "کاروسل محصولات"}
                </span>
                <span className="rounded-full bg-primary px-2 py-0.5 text-[10px] font-bold text-white">
                  {cfg.carousel.maxItems} مورد
                </span>
              </div>
              <div
                className={cn(
                  "flex gap-2 overflow-hidden",
                  cfg.carousel.layoutPreset === "stack" && "flex-col",
                )}
              >
                {cfg.carousel.previewTitles.slice(0, cfg.carousel.maxItems).map((title, ti) => (
                  <div
                    key={title}
                    className={cn(
                      "min-w-[88px] rounded-xl p-2",
                      (cfg.carousel.stylePreset ?? "rail-soft") === "cards-elevated"
                        ? "bg-[#F5F5F5]"
                        : "bg-white/90 text-ink",
                      (cfg.carousel.stylePreset ?? "rail-soft") === "spotlight" &&
                        ti === 0 &&
                        "min-w-[120px] scale-105",
                    )}
                  >
                    <div className="mb-2 h-14 rounded-lg bg-gradient-to-br from-[#F5F5F5] to-[#E7E7E7]" />
                    <div className="truncate text-[10px] font-bold">{title}</div>
                  </div>
                ))}
              </div>
            </div>
          </Draggable>
        ) : null}
      </div>

      {/* Desktop dock preview only — mobile Storefront has categories outside the hero */}
      {featuredOrbs.length && !mobilePreset ? (
        <div className="pointer-events-none absolute inset-x-0 bottom-0 z-40 pb-3 pt-16">
          <div
            aria-hidden
            className="absolute inset-x-0 bottom-0 h-28 bg-[linear-gradient(to_top,rgba(0,0,0,0.5),transparent)]"
          />
          <div className="relative flex items-end justify-center gap-2.5 px-3">
            {featuredOrbs.map((orb, i) => {
              const selected = i === activeOrbIndex;
              return (
                <button
                  key={orb.key}
                  type="button"
                  className="pointer-events-auto flex flex-col items-center"
                  onClick={() => onSelectOrb?.(orb.key)}
                >
                  <div
                    className={cn(
                      "grid h-9 w-9 place-items-center rounded-full text-white transition",
                      selected
                        ? "scale-110 bg-white/28 shadow-[0_8px_20px_rgba(0,0,0,0.25)]"
                        : "scale-95 bg-white/10 opacity-50",
                    )}
                  >
                    <DockIcon name={orb.icon} size={14} />
                  </div>
                  <span
                    className={cn(
                      "mt-1 max-w-[3.2rem] min-h-[2.75em] line-clamp-2 text-center text-[7px] font-semibold leading-snug text-white",
                      !selected && "opacity-40",
                    )}
                  >
                    {orb.name}
                  </span>
                </button>
              );
            })}
            <div className="flex flex-col items-center">
              <div className="grid h-9 w-9 place-items-center rounded-full bg-[#D02327] text-white shadow-[0_8px_20px_rgba(208,35,39,0.35)]">
                <DockIcon name="Category" size={14} />
              </div>
              <span className="mt-1 min-h-[2.75em] text-center text-[7px] font-semibold leading-snug text-white/90">
                همه
              </span>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
