/**
 * Curated homepage/megamenu category tile art (local public assets).
 * Prefer these over API packshots for L1 roots.
 */

export const CATEGORY_IMAGE_BY_ID: Record<number, string> = {
  1: "/images/categories/toolholding.jpg",
  2: "/images/categories/insert-tools.jpg",
  4: "/images/categories/endmills.jpg",
  5: "/images/categories/drills.jpg",
  6: "/images/categories/taps.jpg",
  8: "/images/categories/workholding.jpg",
  9: "/images/categories/machines.jpg",
  56: "/images/categories/metrology-precision.jpg",
  81: "/images/categories/metrology-cnc.jpg",
  87: "/images/categories/metrology-lab.jpg",
  154: "/images/categories/accessories.jpg",
  165: "/images/categories/inserts.jpg",
  186: "/images/categories/helicoil-spring.jpg",
  187: "/images/categories/helicoil-tap.jpg",
  188: "/images/categories/helicoil-kit.jpg",
};

export const CATEGORY_IMAGE_BY_NAME: Record<string, string> = {
  ابزارگیر: CATEGORY_IMAGE_BY_ID[1],
  "ابزار گیر": CATEGORY_IMAGE_BY_ID[1],
  "ابزار اینسرتی": CATEGORY_IMAGE_BY_ID[2],
  اینسرت: CATEGORY_IMAGE_BY_ID[165],
  "ابزار انگشتی": CATEGORY_IMAGE_BY_ID[4],
  "فرز انگشتی": CATEGORY_IMAGE_BY_ID[4],
  مته: CATEGORY_IMAGE_BY_ID[5],
  قلاویز: CATEGORY_IMAGE_BY_ID[6],
  "ابزار گیرشی": CATEGORY_IMAGE_BY_ID[8],
  "دستگاه‌های صنعتی": CATEGORY_IMAGE_BY_ID[9],
  "دستگاه های صنعتی": CATEGORY_IMAGE_BY_ID[9],
  "اندازه گیری دقیق": CATEGORY_IMAGE_BY_ID[56],
  "اندازه‌گیری دقیق": CATEGORY_IMAGE_BY_ID[56],
  اندازه‌گیری: CATEGORY_IMAGE_BY_ID[56],
  "اندازه گیری": CATEGORY_IMAGE_BY_ID[56],
  "CNC اندازه گیری": CATEGORY_IMAGE_BY_ID[81],
  "اندازه گیری فرز CNC": CATEGORY_IMAGE_BY_ID[81],
  "اندازه گیری آزمایشگاهی": CATEGORY_IMAGE_BY_ID[87],
  "لوازم جانبی صنعتی": CATEGORY_IMAGE_BY_ID[154],
  "روغن و روانکار": CATEGORY_IMAGE_BY_ID[154],
  "هلی کویل": CATEGORY_IMAGE_BY_ID[186],
  "فنر هلی کویل": CATEGORY_IMAGE_BY_ID[186],
  "قلاویز هلی کویل": CATEGORY_IMAGE_BY_ID[187],
  "کیت کامل هلی کویل": CATEGORY_IMAGE_BY_ID[188],
  "ابزار کارگاهی : دریل عادی": CATEGORY_IMAGE_BY_ID[5],
  "ابزار کارگاهی": CATEGORY_IMAGE_BY_ID[5],
};

export function normalizeCategoryName(name: string): string {
  return name.trim().replace(/\u200c/g, "").replace(/ي/g, "ی").replace(/ك/g, "ک");
}

/** Resolve tile image: curated id → curated name → API image_url (skip tiny icon assets). */
export function resolveCategoryImage(node: {
  id: number;
  name: string;
  image_url?: string | null;
}): string | null {
  if (CATEGORY_IMAGE_BY_ID[node.id]) return CATEGORY_IMAGE_BY_ID[node.id];
  const byName = CATEGORY_IMAGE_BY_NAME[normalizeCategoryName(node.name)];
  if (byName) return byName;
  const url = node.image_url ?? null;
  if (url && url.includes("/category-icons/")) return null;
  return url;
}
