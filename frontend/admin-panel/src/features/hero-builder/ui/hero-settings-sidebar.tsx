"use client";

import { useState } from "react";
import {
  DS_BUTTON_SIZES,
  DS_BUTTON_STYLES,
  DS_CAROUSEL_LAYOUTS,
  DS_CAROUSEL_STYLES,
  HERO_ANIMATION_PRESETS,
  HERO_BADGE_KINDS,
  HERO_BADGE_STYLES,
  useHeroBuilderStore,
  type HeroBadgeKind,
  type HeroBadgeStyle,
  type ButtonActionType,
  type DsButtonSize,
  type DsButtonStyle,
  type DsCarouselLayout,
  type DsCarouselStyle,
  type OverlayMode,
  type TextAlign,
} from "@/entities/hero";
import {
  ColorField,
  GradientBuilder,
  OpacitySlider,
  PanelSection,
  XYPad,
} from "@/shared/ui";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";
import { ProductPickerModal } from "./product-picker-modal";

export function HeroSettingsSidebar() {
  const store = useHeroBuilderStore();
  const config = store.activeConfig();
  const selected = store.selectedLayerId;
  const [pickerOpen, setPickerOpen] = useState(false);
  const dragLocked = store.project.previewDevice === "mobile";

  return (
    <div className="flex min-w-0 flex-col gap-3 pb-8">
      {dragLocked ? (
        <div className="rounded-xl bg-amber-500/10 px-3 py-2 text-[11px] font-bold leading-relaxed text-amber-800">
          حالت موبایل: چیدمان از قالب اسلاید. فقط عنوان، زیرعنوان و دکمه‌ها را ویرایش کنید — پد موقعیت مخفی است.
        </div>
      ) : null}

      {!dragLocked ? (
      <PanelSection
        title="پس‌زمینه و اورلی"
        hint="تصویر، فوکال، گرادیان"
        active={selected === "background"}
        onActivate={() => store.selectLayer("background")}
        defaultOpen
      >
        <div className="flex gap-2">
          {(["image", "color"] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => store.setBackground({ mode })}
              className={cn(
                "flex-1 rounded-xl px-3 py-2 text-xs font-bold shadow-soft",
                config.background.mode === mode
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-ink",
              )}
            >
              {mode === "image" ? "تصویر" : "رنگ تخت"}
            </button>
          ))}
        </div>

        {config.background.mode === "image" ? (
          <div className="space-y-2">
            <Label>آدرس تصویر</Label>
            <Input
              dir="ltr"
              value={config.background.imageUrl}
              onChange={(e) => store.setBackground({ imageUrl: e.target.value })}
              placeholder="/images/hero/..."
            />
            <Label>فوکال تصویر</Label>
            <div className="flex flex-wrap gap-1.5">
              {["center", "left center", "right center", "center top", "center bottom"].map((focal) => (
                <button
                  key={focal}
                  type="button"
                  onClick={() => store.setBackground({ focal })}
                  className={cn(
                    "rounded-lg px-2 py-1 text-[10px] font-bold",
                    config.background.focal === focal
                      ? "bg-ink text-white"
                      : "bg-muted text-ink",
                  )}
                >
                  {focal}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <ColorField
            label="رنگ پس‌زمینه"
            value={config.background.color}
            onChange={(color) => store.setBackground({ color })}
          />
        )}

        <div className="flex gap-2">
          {(["solid", "gradient"] as OverlayMode[]).map((mode) => (
            <button
              key={mode}
              type="button"
              onClick={() => store.setOverlay({ mode })}
              className={cn(
                "flex-1 rounded-xl px-3 py-2 text-xs font-bold shadow-soft",
                config.overlay.mode === mode ? "bg-ink text-white" : "bg-muted text-ink",
              )}
            >
              {mode === "solid" ? "اورلی ساده" : "گرادیان"}
            </button>
          ))}
        </div>

        {config.overlay.mode === "solid" ? (
          <ColorField
            label="رنگ اورلی"
            value={config.overlay.solidColor}
            onChange={(solidColor) => store.setOverlay({ solidColor })}
            allowAlpha
          />
        ) : (
          <GradientBuilder
            from={config.overlay.gradientFrom}
            to={config.overlay.gradientTo}
            angle={config.overlay.gradientAngle}
            onFrom={(gradientFrom) => store.setOverlay({ gradientFrom })}
            onTo={(gradientTo) => store.setOverlay({ gradientTo })}
            onAngle={(gradientAngle) => store.setOverlay({ gradientAngle })}
          />
        )}

        <OpacitySlider
          label="شفافیت اورلی"
          value={config.overlay.opacity}
          onChange={(opacity) => store.setOverlay({ opacity })}
        />
        <div className="flex flex-col gap-2">
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">ارتفاع کانواس</span>
            <span className="font-bold tabular-nums">{config.minHeight}px</span>
          </div>
          <input
            type="range"
            min={400}
            max={720}
            step={10}
            value={config.minHeight}
            onChange={(e) => store.patchConfig({ minHeight: Number(e.target.value) })}
            className="h-2 w-full appearance-none rounded-full bg-border accent-primary"
          />
        </div>
      </PanelSection>
      ) : null}

      <PanelSection
        title="تایپوگرافی"
        hint={dragLocked ? "متن اسلاید موبایل" : "عنوان و موقعیت — یا روی کانواس بکشید"}
        active={selected === "typography"}
        onActivate={() => store.selectLayer("typography")}
        defaultOpen={dragLocked}
      >
        <Input
          value={config.typography.title}
          onChange={(e) => store.setTypography({ title: e.target.value })}
          placeholder="عنوان"
        />
        <Input
          value={config.typography.subtitle}
          onChange={(e) => store.setTypography({ subtitle: e.target.value })}
          placeholder="زیرعنوان"
        />
        <div className="grid grid-cols-2 gap-3">
          <ColorField
            label="رنگ عنوان"
            value={config.typography.titleColor}
            onChange={(titleColor) => store.setTypography({ titleColor })}
          />
          <ColorField
            label="رنگ زیرعنوان"
            value={config.typography.subtitleColor.startsWith("#")
              ? config.typography.subtitleColor
              : "#FFFFFF"}
            onChange={(subtitleColor) => store.setTypography({ subtitleColor })}
          />
        </div>
        <div className="flex flex-col gap-2">
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">سایز عنوان</span>
            <span className="font-bold">{config.typography.titleSize}px</span>
          </div>
          <input
            type="range"
            min={22}
            max={64}
            value={config.typography.titleSize}
            onChange={(e) => store.setTypography({ titleSize: Number(e.target.value) })}
            className="h-2 w-full appearance-none rounded-full bg-border accent-primary"
          />
        </div>
        {!dragLocked ? (
          <>
            <div className="flex gap-2">
              {(["start", "center", "end"] as TextAlign[]).map((align) => (
                <button
                  key={align}
                  type="button"
                  onClick={() => store.setTypography({ align })}
                  className={cn(
                    "flex-1 rounded-xl px-2 py-2 text-[11px] font-bold shadow-soft",
                    config.typography.align === align
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-ink",
                  )}
                >
                  {align === "start" ? "راست" : align === "center" ? "وسط" : "چپ"}
                </button>
              ))}
            </div>
            <XYPad
              label="موقعیت متن"
              value={config.typography.position}
              onChange={(position) => store.setTypography({ position })}
            />
          </>
        ) : null}
      </PanelSection>

      <PanelSection
        title="دکمه‌ها"
        hint={dragLocked ? "برچسب و استایل — موقعیت از قالب" : "فقط استایل‌های دیزاین‌سیستم"}
        active={selected?.startsWith("btn") || selected === "buttons"}
        onActivate={() => store.selectLayer("buttons")}
        defaultOpen={dragLocked}
      >
        <Button type="button" variant="secondary" className="w-full" onClick={store.addButton}>
          + دکمه جدید
        </Button>
        {config.buttons.map((button) => {
          const stylePreset = (button.stylePreset ?? "primary") as DsButtonStyle;
          const sizePreset = (button.sizePreset ?? "md") as DsButtonSize;
          return (
            <div
              key={button.id}
              className={cn(
                "min-w-0 space-y-3 overflow-hidden rounded-2xl bg-muted/50 p-3 ring-1 ring-inset",
                selected === button.id ? "ring-primary" : "ring-border",
              )}
              onClick={() => store.selectLayer(button.id)}
            >
              <div className="flex min-w-0 gap-2">
                <Input
                  className="min-w-0"
                  value={button.label}
                  onChange={(e) => store.updateButton(button.id, { label: e.target.value })}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="shrink-0"
                  onClick={() => store.removeButton(button.id)}
                >
                  حذف
                </Button>
              </div>
              <div>
                <div className="mb-1.5 text-[10px] font-bold text-muted-foreground">استایل</div>
                <div className="grid grid-cols-2 gap-1.5">
                  {DS_BUTTON_STYLES.map((s) => (
                    <button
                      key={s.id}
                      type="button"
                      onClick={() => store.updateButton(button.id, { stylePreset: s.id })}
                      className={cn(
                        "rounded-xl px-2 py-2 text-start",
                        stylePreset === s.id
                          ? "bg-ink text-white"
                          : "bg-card text-ink shadow-soft",
                      )}
                    >
                      <div className="text-[11px] font-bold">{s.label}</div>
                      <div className="text-[9px] opacity-70">{s.hint}</div>
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <div className="mb-1.5 text-[10px] font-bold text-muted-foreground">سایز</div>
                <div className="flex flex-wrap gap-1.5">
                  {DS_BUTTON_SIZES.map((s) => (
                    <button
                      key={s.id}
                      type="button"
                      onClick={() => store.updateButton(button.id, { sizePreset: s.id })}
                      className={cn(
                        "rounded-lg px-2.5 py-1.5 text-[10px] font-bold",
                        sizePreset === s.id ? "bg-primary text-white" : "bg-card shadow-soft",
                      )}
                    >
                      {s.label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="grid grid-cols-3 gap-1.5">
                {(["href", "modal", "fn"] as ButtonActionType[]).map((type) => (
                  <button
                    key={type}
                    type="button"
                    onClick={() =>
                      store.updateButton(button.id, { action: { ...button.action, type } })
                    }
                    className={cn(
                      "rounded-lg px-2 py-1.5 text-[10px] font-bold",
                      button.action.type === type
                        ? "bg-primary text-primary-foreground"
                        : "bg-card shadow-soft",
                    )}
                  >
                    {type === "href" ? "لینک" : type === "modal" ? "مودال" : "تابع"}
                  </button>
                ))}
              </div>
              <Input
                dir="ltr"
                className="min-w-0"
                value={button.action.value}
                onChange={(e) =>
                  store.updateButton(button.id, {
                    action: { ...button.action, value: e.target.value },
                  })
                }
              />
              {!dragLocked ? (
                <XYPad
                  label="موقعیت"
                  value={button.position}
                  onChange={(position) => store.updateButton(button.id, { position })}
                />
              ) : null}
            </div>
          );
        })}
      </PanelSection>

      {!dragLocked ? (
      <PanelSection
        title="بج‌های کمپین"
        hint="تخفیف، فروش ویژه، اعتماد…"
        active={selected?.startsWith("badge") || selected === "badges"}
        onActivate={() => store.selectLayer("badges")}
      >
        <div className="grid grid-cols-2 gap-2">
          {HERO_BADGE_KINDS.map((kind) => (
            <button
              key={kind.id}
              type="button"
              onClick={() => store.addBadge(kind.id)}
              className="rounded-xl bg-muted px-2 py-2 text-[11px] font-bold shadow-soft hover:bg-accent"
            >
              + {kind.label}
            </button>
          ))}
        </div>
        {config.badges.map((badge) => (
          <div
            key={badge.id}
            className={cn(
              "space-y-3 rounded-2xl bg-muted/50 p-3 ring-1 ring-inset",
              selected === badge.id ? "ring-primary" : "ring-border",
            )}
            onClick={() => store.selectLayer(badge.id)}
          >
            <div className="flex gap-2">
              <select
                className="h-10 flex-1 rounded-xl bg-card px-3 text-sm font-bold shadow-soft"
                value={badge.kind}
                onChange={(e) =>
                  store.updateBadge(badge.id, { kind: e.target.value as HeroBadgeKind })
                }
              >
                {HERO_BADGE_KINDS.map((k) => (
                  <option key={k.id} value={k.id}>
                    {k.label}
                  </option>
                ))}
              </select>
              <Button type="button" variant="ghost" size="sm" onClick={() => store.removeBadge(badge.id)}>
                حذف
              </Button>
            </div>
            <Input
              value={badge.label}
              onChange={(e) => store.updateBadge(badge.id, { label: e.target.value })}
            />
            <Input
              value={badge.meta ?? ""}
              onChange={(e) => store.updateBadge(badge.id, { meta: e.target.value })}
              placeholder="متا"
            />
            <div className="flex flex-wrap gap-1.5">
              {HERO_BADGE_STYLES.map((style) => (
                <button
                  key={style.id}
                  type="button"
                  onClick={() =>
                    store.updateBadge(badge.id, { style: style.id as HeroBadgeStyle })
                  }
                  className={cn(
                    "rounded-lg px-2 py-1 text-[10px] font-bold",
                    badge.style === style.id ? "bg-ink text-white" : "bg-card shadow-soft",
                  )}
                >
                  {style.label}
                </button>
              ))}
            </div>
            <div className="flex items-center justify-between rounded-xl bg-card px-3 py-2">
              <span className="text-xs text-muted-foreground">انیمیشن بج</span>
              <Switch
                checked={badge.animated}
                onCheckedChange={(animated) => store.updateBadge(badge.id, { animated })}
              />
            </div>
            <XYPad
              label="موقعیت"
              value={badge.position}
              onChange={(position) => store.updateBadge(badge.id, { position })}
            />
          </div>
        ))}
      </PanelSection>
      ) : null}

      {!dragLocked ? (
      <PanelSection
        title="کاروسل محصول"
        hint="استایل دیزاین‌سیستم + انتخاب محصول"
        active={selected === "carousel"}
        onActivate={() => store.selectLayer("carousel")}
      >
        <div className="flex items-center justify-between rounded-xl bg-muted px-3 py-2">
          <span className="text-sm font-bold">فعال</span>
          <Switch
            checked={config.carousel.enabled}
            onCheckedChange={(enabled) => store.setCarousel({ enabled })}
          />
        </div>
        {config.carousel.enabled ? (
          <>
            <Input
              className="min-w-0"
              value={config.carousel.categoryLabel}
              onChange={(e) => store.setCarousel({ categoryLabel: e.target.value })}
              placeholder="عنوان کروسل"
            />
            <div>
              <div className="mb-1.5 text-[10px] font-bold text-muted-foreground">استایل</div>
              <div className="grid grid-cols-2 gap-1.5">
                {DS_CAROUSEL_STYLES.map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() =>
                      store.setCarousel({ stylePreset: s.id as DsCarouselStyle })
                    }
                    className={cn(
                      "rounded-xl px-2 py-2 text-start",
                      (config.carousel.stylePreset ?? "rail-soft") === s.id
                        ? "bg-ink text-white"
                        : "bg-card shadow-soft",
                    )}
                  >
                    <div className="text-[11px] font-bold">{s.label}</div>
                    <div className="text-[9px] opacity-70">{s.hint}</div>
                  </button>
                ))}
              </div>
            </div>
            <div>
              <div className="mb-1.5 text-[10px] font-bold text-muted-foreground">چیدمان</div>
              <div className="flex flex-wrap gap-1.5">
                {DS_CAROUSEL_LAYOUTS.map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() =>
                      store.setCarousel({ layoutPreset: s.id as DsCarouselLayout })
                    }
                    className={cn(
                      "rounded-lg px-2.5 py-1.5 text-[10px] font-bold",
                      (config.carousel.layoutPreset ?? "row-comfortable") === s.id
                        ? "bg-primary text-white"
                        : "bg-card shadow-soft",
                    )}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex flex-col gap-2">
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">تعداد آیتم</span>
                <span className="font-bold">{config.carousel.maxItems}</span>
              </div>
              <input
                type="range"
                min={2}
                max={6}
                value={config.carousel.maxItems}
                onChange={(e) => store.setCarousel({ maxItems: Number(e.target.value) })}
                className="h-2 w-full appearance-none rounded-full bg-border accent-primary"
              />
            </div>
            <Button type="button" variant="outline" className="w-full" onClick={() => setPickerOpen(true)}>
              انتخاب محصولات ({config.carousel.productIds?.length ?? 0})
            </Button>
            {(config.carousel.previewTitles?.length ?? 0) > 0 ? (
              <p className="truncate text-[10px] text-muted-foreground">
                {config.carousel.previewTitles.slice(0, 4).join(" · ")}
              </p>
            ) : null}
            <XYPad
              label="موقعیت"
              value={config.carousel.position}
              onChange={(position) => store.setCarousel({ position })}
            />
          </>
        ) : null}
      </PanelSection>
      ) : null}

      {!dragLocked ? (
      <ProductPickerModal
        open={pickerOpen}
        onOpenChange={setPickerOpen}
        selectedIds={config.carousel.productIds ?? []}
        maxItems={config.carousel.maxItems}
        onConfirm={(ids, titles) =>
          store.setCarousel({
            productIds: ids,
            previewTitles: titles,
            maxItems: Math.max(ids.length, 2),
          })
        }
      />
      ) : null}

      {!dragLocked ? (
      <PanelSection
        title="انیمیشن"
        active={selected === "animation"}
        onActivate={() => store.selectLayer("animation")}
      >
        <div className="grid gap-2">
          {HERO_ANIMATION_PRESETS.map((preset) => (
            <button
              key={preset.id}
              type="button"
              onClick={() => store.setAnimation(preset.id)}
              className={cn(
                "rounded-2xl px-3 py-3 text-start shadow-soft",
                config.animation === preset.id
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-ink hover:bg-accent",
              )}
            >
              <div className="text-sm font-bold">{preset.label}</div>
              <div className="mt-0.5 text-[11px] opacity-80">{preset.description}</div>
            </button>
          ))}
        </div>
      </PanelSection>
      ) : null}
    </div>
  );
}
