/** Design-system presets for hero widgets — no freeform styling. */

export type DsButtonStyle = "primary" | "soft" | "on-dark-glass" | "on-dark-outline";
export type DsButtonSize = "sm" | "md" | "lg" | "pill";

export type DsCarouselStyle = "rail-soft" | "cards-elevated" | "strip-minimal" | "spotlight";
export type DsCarouselLayout = "row-compact" | "row-comfortable" | "row-large" | "stack";

export type DsCardStyle = "glass" | "solid" | "minimal" | "accent";
export type DsCardLayout = "horizontal" | "vertical" | "compact" | "featured";

export type MobileComposePreset = "balanced" | "copy-focus" | "media-focus" | "dock-first";

export const DS_BUTTON_STYLES: {
  id: DsButtonStyle;
  label: string;
  hint: string;
}[] = [
  { id: "primary", label: "اصلی قرمز", hint: "CTA اصلی کارزار" },
  { id: "soft", label: "سافت خاکستری", hint: "اقدام ثانویه" },
  { id: "on-dark-glass", label: "شیشه روی تیره", hint: "روی تصویر هیرو" },
  { id: "on-dark-outline", label: "خطی روشن", hint: "کم‌رنگ روی تیره" },
];

export const DS_BUTTON_SIZES: { id: DsButtonSize; label: string }[] = [
  { id: "sm", label: "کوچک" },
  { id: "md", label: "متوسط" },
  { id: "lg", label: "بزرگ" },
  { id: "pill", label: "قرصی" },
];

export const DS_CAROUSEL_STYLES: {
  id: DsCarouselStyle;
  label: string;
  hint: string;
}[] = [
  { id: "rail-soft", label: "ریل نرم", hint: "کارت‌های نیمه‌شفاف" },
  { id: "cards-elevated", label: "کارت برجسته", hint: "سفید با سایه" },
  { id: "strip-minimal", label: "نوار مینیمال", hint: "سبک و کم‌جزئیات" },
  { id: "spotlight", label: "اسپات‌لایت", hint: "کارت اول بزرگ‌تر" },
];

export const DS_CAROUSEL_LAYOUTS: { id: DsCarouselLayout; label: string }[] = [
  { id: "row-compact", label: "افقی فشرده" },
  { id: "row-comfortable", label: "افقی راحت" },
  { id: "row-large", label: "افقی بزرگ" },
  { id: "stack", label: "عمودی" },
];

export const MOBILE_COMPOSE_PRESETS: {
  id: MobileComposePreset;
  label: string;
  hint: string;
  /** Short visual cue for preset cards */
  visual: string;
}[] = [
  {
    id: "dock-first",
    label: "چیدمان فشرده",
    hint: "فقط چیدمان متن و CTA — داک موبایل خارج هیرو (بخش دسته‌ها)",
    visual: "فشرده",
  },
  {
    id: "copy-focus",
    label: "تمرکز متن",
    hint: "تیتر درشت و CTA اصلی — بدون داک داخل هیرو",
    visual: "متن بزرگ",
  },
  {
    id: "media-focus",
    label: "تمرکز تصویر",
    hint: "تصویر فول‌بلید؛ کپی پایین — بدون داک داخل هیرو",
    visual: "تصویر باز",
  },
  {
    id: "balanced",
    label: "متعادل",
    hint: "تعادل متن و دکمه — پیش‌فرض امن (داک در بخش جدا)",
    visual: "متعادل",
  },
];

export function buttonStyleCss(style: DsButtonStyle): {
  background: string;
  color: string;
  border?: string;
  backdropFilter?: string;
} {
  switch (style) {
    case "soft":
      return { background: "#5E5F5E", color: "#FFFFFF" };
    case "on-dark-glass":
      return {
        background: "rgba(255,255,255,0.14)",
        color: "#FFFFFF",
        backdropFilter: "blur(12px)",
      };
    case "on-dark-outline":
      return {
        background: "transparent",
        color: "#FFFFFF",
        border: "1.5px solid rgba(255,255,255,0.55)",
      };
    case "primary":
    default:
      return { background: "#D02327", color: "#FFFFFF" };
  }
}

export function buttonSizeCss(size: DsButtonSize): {
  padding: string;
  fontSize: string;
  borderRadius: number;
} {
  switch (size) {
    case "sm":
      return { padding: "0.45rem 0.9rem", fontSize: "0.75rem", borderRadius: 10 };
    case "lg":
      return { padding: "0.85rem 1.4rem", fontSize: "0.95rem", borderRadius: 14 };
    case "pill":
      return { padding: "0.7rem 1.35rem", fontSize: "0.875rem", borderRadius: 999 };
    case "md":
    default:
      return { padding: "0.65rem 1.15rem", fontSize: "0.875rem", borderRadius: 12 };
  }
}
