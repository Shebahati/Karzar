/**
 * Generates a large category tree and product catalog for mega-menu stress testing.
 * Keeps the original seed items and expands programmatically.
 */

import type { Category } from "@/types/category";
import type { ProductDetail } from "@/types/product";

type RawProduct = Omit<ProductDetail, "category" | "brand" | "stock_status"> & {
  category_id: number;
  brand_id: number | null;
};

const IMG = (seed: string) => `https://picsum.photos/seed/${seed}/800/800`;

const L1_NAMES = [
  "ابزار برقی",
  "ابزار دستی",
  "ابزار اندازه‌گیری",
  "تجهیزات کارگاهی",
  "ابزار بادی و پنوماتیک",
  "جوش و برش",
  "ایمنی و حفاظت فردی",
  "لوازم جانبی و مصرفی",
  "ابزار باغبانی",
  "رفع‌سازی و نگهداری",
  "ابزار دقیق‌سازی",
  "حمل‌ونقل و انبارداری",
];

const L2_SUFFIXES = ["صنعتی", "حرفه‌ای", "نیمه‌صنعتی", "سبک", "سنگین", "تخصصی"];
const L3_SUFFIXES = ["سری استاندارد", "سری پیشرفته", "سری اقتصادی", "سری حرفه‌ای"];

export function expandCategories(base: Category[]): Category[] {
  const categories: Category[] = [...base];
  let nextId =
    Math.max(...base.map((c) => c.id), 0) + 100;

  for (const l1Name of L1_NAMES) {
    const exists = categories.some((c) => c.name === l1Name && c.parent_id === null);
    if (exists) continue;

    const l1Id = nextId++;
    categories.push({ id: l1Id, name: l1Name, parent_id: null });

    for (const l2Suffix of L2_SUFFIXES) {
      const l2Id = nextId++;
      categories.push({
        id: l2Id,
        name: `${l1Name} ${l2Suffix}`,
        parent_id: l1Id,
      });

      for (const l3Suffix of L3_SUFFIXES) {
        categories.push({
          id: nextId++,
          name: `${l2Suffix} — ${l3Suffix}`,
          parent_id: l2Id,
        });
      }
    }
  }

  return categories;
}

export function expandProducts(
  base: RawProduct[],
  categories: Category[],
): RawProduct[] {
  const leafIds = categories.filter((c) => {
    const hasChild = categories.some((x) => x.parent_id === c.id);
    return !hasChild;
  }).map((c) => c.id);

  const products: RawProduct[] = [...base];
  let nextId = Math.max(...base.map((p) => p.id), 0) + 1;

  const templates = base.slice(0, Math.min(6, base.length));
  const brandIds = [...new Set(base.map((p) => p.brand_id).filter(Boolean))] as number[];

  for (let i = 0; i < leafIds.length; i++) {
    const leafId = leafIds[i];
    if (base.some((p) => p.category_id === leafId)) continue;

    const template = templates[i % templates.length];
    const variant = Math.floor(i / templates.length) + 1;
    const brandId = brandIds[i % brandIds.length] ?? template.brand_id;

    products.push({
      ...template,
      id: nextId,
      sku: `${template.sku}-V${variant}-${leafId}`,
      name: `${template.name} — مدل ${variant}`,
      category_id: leafId,
      brand_id: brandId,
      thumbnail: IMG(`p-${nextId}`),
      images: [{ id: nextId * 10, url: IMG(`p-${nextId}`), is_primary: true }],
      base_price: template.base_price
        ? String(Math.round(Number(template.base_price) * (0.85 + (i % 5) * 0.05)))
        : null,
      stock_quantity: String(5 + (i % 40)),
      low_stock: i % 7 === 0,
      created_at: template.created_at,
      updated_at: template.updated_at,
    });
    nextId++;
  }

  return products;
}

export function expandCategoryIcons(
  base: Record<number, string>,
  categories: Category[],
): Record<number, string> {
  const icons = ["Activity", "Setting", "Filter2", "Work", "Bag", "Buy", "Category", "Star"];
  const result = { ...base };
  for (const c of categories) {
    if (c.parent_id === null && !result[c.id]) {
      result[c.id] = icons[c.id % icons.length];
    }
  }
  return result;
}
