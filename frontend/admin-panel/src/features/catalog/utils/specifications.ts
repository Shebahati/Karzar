import type { CategoryFlat } from "@/types/category";
import type { CategorySpecTemplate } from "@/types/spec-template";
import { enrichFlatCategories, isLayer3Leaf } from "@/features/catalog/utils/category-tree";

/** Layer-3 leaf categories only (depth 3, exactly two ancestors, no children). */
export function getSelectableCategories(categories: CategoryFlat[]): CategoryFlat[] {
  return enrichFlatCategories(categories).filter((c) =>
    isLayer3Leaf(c.depth, c.is_leaf),
  );
}

export function formatCategoryLabel(category: CategoryFlat): string {
  if (category.breadcrumb.length <= 1) return category.name;
  return category.breadcrumb.join(" / ");
}

export function findCategoryById(
  categories: CategoryFlat[],
  id: number,
): CategoryFlat | undefined {
  return categories.find((c) => c.id === id);
}

export function buildComboboxOptions(
  suggestions: string[],
  currentValue: string,
): string[] {
  const merged = new Set(suggestions.map((s) => s.trim()).filter(Boolean));
  const trimmed = currentValue.trim();
  if (trimmed) merged.add(trimmed);
  return Array.from(merged);
}

export function defaultSpecificationsFromTemplate(
  template: CategorySpecTemplate,
): SpecificationsFormValues {
  const toggles: Record<string, boolean> = {};
  const details: Record<string, string | string[]> = {};

  for (const feature of template.features) {
    const raw = template.default_values.features[feature.key];
    toggles[feature.key] = typeof raw === "boolean" ? raw : false;
    if (feature.detail) {
      const detailRaw = template.default_values.features[feature.detail.key];
      if (feature.detail.type === "string_array") {
        details[feature.detail.key] = Array.isArray(detailRaw) ? detailRaw : [];
      } else {
        details[feature.detail.key] =
          typeof detailRaw === "string" ? detailRaw : "";
      }
    }
  }

  return {
    technical_specs: template.default_values.technical_specs.map((row) => ({
      key: row.key,
      value: row.value ?? "",
    })),
    featureToggles: toggles,
    featureDetails: details,
    dimensions: template.default_values.dimensions.map((row) => ({
      key: row.key,
      value: row.value === null || row.value === undefined ? "" : String(row.value),
    })),
  };
}

/** Form shape for the 3-part specifications section. */
export interface SpecificationsFormValues {
  technical_specs: { key: string; value: string }[];
  featureToggles: Record<string, boolean>;
  featureDetails: Record<string, string | string[]>;
  dimensions: { key: string; value: string }[];
}

export const emptySpecifications: SpecificationsFormValues = {
  technical_specs: [{ key: "", value: "" }],
  featureToggles: {},
  featureDetails: {},
  dimensions: [{ key: "", value: "" }],
};
