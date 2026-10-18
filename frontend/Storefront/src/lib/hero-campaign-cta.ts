import { FINAL_L1_CATEGORIES } from "@/config/l1-categories";
import type { CategoryTreeNode } from "@/types/category";
import type { DesignedHeroSlide } from "@/types/hero-design";

function normalized(value: string): string {
  return value.trim().replace(/\u200c/g, " ").replace(/ي/g, "ی").replace(/ك/g, "ک").replace(/\s+/g, " ").toLowerCase();
}

function findLiveCategory(
  nodes: CategoryTreeNode[],
  definition: (typeof FINAL_L1_CATEGORIES)[number],
): CategoryTreeNode | undefined {
  const aliases = new Set([definition.name, ...definition.aliases].map(normalized));
  const expectedSlug = normalized(definition.slug);
  const exactMatches: CategoryTreeNode[] = [];
  const walk = (list: CategoryTreeNode[]) => {
    for (const node of list) {
      if (normalized(node.slug ?? "") === expectedSlug || aliases.has(normalized(node.name))) {
        exactMatches.push(node);
      }
      walk(node.subcategories ?? []);
    }
  };
  walk(nodes);
  // Ambiguous category identity must not guess an ID or send visitors to a 404 hub.
  return exactMatches.length === 1 ? exactMatches[0] : undefined;
}

/**
 * Convert only the five known, old static hero category hrefs to live catalog
 * filters. Never generate /categories/{guessed-slug}: a valid-looking slug may
 * legitimately be absent/empty and the CategoryHub returns a hard 404.
 * An unresolvable category uses a labeled catalog search, not all products.
 * Admin-customized CTA destinations remain untouched.
 */
export function resolveCampaignHeroCtas(
  slide: DesignedHeroSlide,
  roots: CategoryTreeNode[],
): DesignedHeroSlide {
  if (!slide.id.startsWith("slide_h0")) return slide;
  let changed = false;
  const buttons = slide.config.buttons.map((button) => {
    if (button.action.type !== "href") return button;
    const definition = FINAL_L1_CATEGORIES.find(
      (def) => button.action.value === `/categories/${def.slug}`,
    );
    if (!definition) return button;
    const category = findLiveCategory(roots, definition);
    const href = category
      ? `/catalog?category=${category.id}`
      : `/catalog?search=${encodeURIComponent(definition.name)}`;
    changed = true;
    return { ...button, action: { ...button.action, value: href } };
  });
  return changed ? { ...slide, config: { ...slide.config, buttons } } : slide;
}
