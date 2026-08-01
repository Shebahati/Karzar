/**
 * Designed L1 category icons (ASCII-safe public URLs).
 * Mirrored from Storefront for admin dock / category form previews.
 */

export const CATEGORY_ICON_DIR = "/category-icons";

export const CATEGORY_ICON_BY_SLUG: Record<string, string> = {
  "andaze-giri": `${CATEGORY_ICON_DIR}/andaze-giri.png`,
  "andaze-giri-daghigh": `${CATEGORY_ICON_DIR}/andaze-giri.png`,
  "andaze-giri-azmayeshgahi": `${CATEGORY_ICON_DIR}/andaze-giri.png`,
  "andaze-giri-cnc": `${CATEGORY_ICON_DIR}/andaze-giri.png`,
  "abzar-inserti": `${CATEGORY_ICON_DIR}/abzar-inserti.png`,
  insert: `${CATEGORY_ICON_DIR}/insert.png`,
  "farz-angoshti": `${CATEGORY_ICON_DIR}/farz-angoshti.png`,
  "abzar-angoshti": `${CATEGORY_ICON_DIR}/farz-angoshti.png`,
  ghalaviz: `${CATEGORY_ICON_DIR}/ghalaviz.png`,
  "abzar-gir": `${CATEGORY_ICON_DIR}/abzar-gir.png`,
  abzargir: `${CATEGORY_ICON_DIR}/abzar-gir.png`,
  "abzar-gireshi": `${CATEGORY_ICON_DIR}/abzar-gireshi.png`,
  "dastgah-sanati": `${CATEGORY_ICON_DIR}/dastgah-sanati.png`,
  "heli-coil": `${CATEGORY_ICON_DIR}/heli-coil.png`,
  mete: `${CATEGORY_ICON_DIR}/mete.png`,
  "abzar-kargahi": `${CATEGORY_ICON_DIR}/abzar-kargahi.png`,
  "abzar-tarashkari": `${CATEGORY_ICON_DIR}/abzar-kargahi.png`,
  "roghan-ravankar": `${CATEGORY_ICON_DIR}/roghan-ravankar.png`,
  "lavazem-janebi": `${CATEGORY_ICON_DIR}/roghan-ravankar.png`,
};

export const CATEGORY_ICON_BY_NAME: Record<string, string> = {
  اندازه‌گیری: CATEGORY_ICON_BY_SLUG["andaze-giri"]!,
  "اندازه گیری": CATEGORY_ICON_BY_SLUG["andaze-giri"]!,
  "اندازه گیری دقیق": CATEGORY_ICON_BY_SLUG["andaze-giri"]!,
  "اندازه‌گیری دقیق": CATEGORY_ICON_BY_SLUG["andaze-giri"]!,
  "اندازه گیری آزمایشگاهی": CATEGORY_ICON_BY_SLUG["andaze-giri"]!,
  "اندازه‌گیری آزمایشگاهی": CATEGORY_ICON_BY_SLUG["andaze-giri"]!,
  "اندازه گیری فرز CNC": CATEGORY_ICON_BY_SLUG["andaze-giri"]!,
  "اندازه‌گیری فرز CNC": CATEGORY_ICON_BY_SLUG["andaze-giri"]!,
  "ابزار اینسرتی": CATEGORY_ICON_BY_SLUG["abzar-inserti"]!,
  اینسرت: CATEGORY_ICON_BY_SLUG.insert!,
  "فرز انگشتی": CATEGORY_ICON_BY_SLUG["farz-angoshti"]!,
  "ابزار انگشتی": CATEGORY_ICON_BY_SLUG["farz-angoshti"]!,
  قلاویز: CATEGORY_ICON_BY_SLUG.ghalaviz!,
  "ابزار گیر": CATEGORY_ICON_BY_SLUG["abzar-gir"]!,
  ابزارگیر: CATEGORY_ICON_BY_SLUG["abzar-gir"]!,
  "ابزار گیرشی": CATEGORY_ICON_BY_SLUG["abzar-gireshi"]!,
  "دستگاه‌های صنعتی": CATEGORY_ICON_BY_SLUG["dastgah-sanati"]!,
  "دستگاه های صنعتی": CATEGORY_ICON_BY_SLUG["dastgah-sanati"]!,
  "هلی کویل": CATEGORY_ICON_BY_SLUG["heli-coil"]!,
  مته: CATEGORY_ICON_BY_SLUG.mete!,
  "ابزار کارگاهی : دریل عادی": CATEGORY_ICON_BY_SLUG["abzar-kargahi"]!,
  "ابزار کارگاهی": CATEGORY_ICON_BY_SLUG["abzar-kargahi"]!,
  "ابزار تراشکاری": CATEGORY_ICON_BY_SLUG["abzar-kargahi"]!,
  "روغن و روانکار": CATEGORY_ICON_BY_SLUG["roghan-ravankar"]!,
  "روغن و زوانکار": CATEGORY_ICON_BY_SLUG["roghan-ravankar"]!,
  "لوازم جانبی صنعتی": CATEGORY_ICON_BY_SLUG["roghan-ravankar"]!,
};

export function normalizeCategoryIconName(name: string): string {
  return name
    .trim()
    .replace(/\u200c/g, " ")
    .replace(/\s+/g, " ")
    .replace(/ي/g, "ی")
    .replace(/ك/g, "ک");
}

export function isCategoryIconUrl(value?: string | null): boolean {
  if (!value) return false;
  const v = value.trim();
  return (
    v.startsWith("/") ||
    v.startsWith("http://") ||
    v.startsWith("https://") ||
    v.startsWith("blob:") ||
    v.startsWith("data:") ||
    /\.(png|jpe?g|webp|gif|svg)(\?|$)/i.test(v)
  );
}

export function resolveCategoryIconUrl(node: {
  name?: string | null;
  icon?: string | null;
  slug?: string | null;
  image_url?: string | null;
}): string | null {
  if (isCategoryIconUrl(node.icon)) return node.icon!.trim();
  if (node.slug) {
    const bySlug = CATEGORY_ICON_BY_SLUG[normalizeCategoryIconName(node.slug)];
    if (bySlug) return bySlug;
  }
  if (node.name) {
    const byName = CATEGORY_ICON_BY_NAME[normalizeCategoryIconName(node.name)];
    if (byName) return byName;
  }
  if (isCategoryIconUrl(node.image_url) && node.image_url!.includes("/category-icons/")) {
    return node.image_url!.trim();
  }
  return null;
}
