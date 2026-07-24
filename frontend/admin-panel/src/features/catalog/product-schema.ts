import { z } from "zod";

import { DEFAULT_TAX_PERCENT } from "@/lib/constants";
import { STOCK_UNITS } from "@/types/product";
import type { ProductCreatePayload, ProductDetail, ProductUpdatePayload } from "@/types/product";
import type { CategorySpecTemplate } from "@/types/spec-template";
import type { SpecificationsFormValues } from "@/features/catalog/utils/specifications";

const optionalNumberString = (opts?: { min?: number; max?: number }) =>
  z
    .string()
    .trim()
    .refine(
      (value) => {
        if (value === "") return true;
        const n = Number(value);
        if (Number.isNaN(n)) return false;
        if (opts?.min !== undefined && n < opts.min) return false;
        if (opts?.max !== undefined && n > opts.max) return false;
        return true;
      },
      { message: "مقدار عددی معتبر وارد کنید." },
    );

const requiredNumberString = (opts?: { min?: number; max?: number }) =>
  z
    .string()
    .trim()
    .min(1, { message: "این فیلد الزامی است." })
    .refine(
      (value) => {
        const n = Number(value);
        if (Number.isNaN(n)) return false;
        if (opts?.min !== undefined && n < opts.min) return false;
        if (opts?.max !== undefined && n > opts.max) return false;
        return true;
      },
      { message: "مقدار عددی معتبر وارد کنید." },
    );

export const keyValueRowSchema = z.object({
  key: z.string().trim(),
  value: z.string().trim(),
});

export const dimensionRowSchema = z.object({
  key: z.string().trim(),
  value: z.string().trim(),
});

export const specificationsFormSchema = z.object({
  technical_specs: z.array(keyValueRowSchema),
  featureToggles: z.record(z.string(), z.boolean()),
  featureDetails: z.record(z.string(), z.union([z.string(), z.array(z.string())])),
  dimensions: z.array(dimensionRowSchema),
});

function isBlankOrValidUrl(value: string): boolean {
  if (value.trim() === "") return true;
  try {
    new URL(value.trim());
    return true;
  } catch {
    return false;
  }
}

function validateKeyValueRows(
  rows: { key: string; value: string }[],
  section: "technical_specs",
  ctx: z.RefinementCtx,
) {
  const seen = new Set<string>();
  rows.forEach((entry, index) => {
    const hasKey = entry.key.length > 0;
    const hasValue = entry.value.length > 0;
    if (hasValue && !hasKey) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["specifications", section, index, "key"],
        message: "نام ویژگی را وارد کنید.",
      });
    }
    if (hasKey && !hasValue) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["specifications", section, index, "value"],
        message: "مقدار ویژگی را وارد کنید.",
      });
    }
    if (hasKey) {
      const normalized = entry.key.toLowerCase();
      if (seen.has(normalized)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["specifications", section, index, "key"],
          message: "این ویژگی تکراری است.",
        });
      }
      seen.add(normalized);
    }
  });
}

function validateDimensionRows(
  rows: { key: string; value: string }[],
  ctx: z.RefinementCtx,
) {
  const seen = new Set<string>();
  rows.forEach((entry, index) => {
    const hasKey = entry.key.length > 0;
    const hasValue = entry.value.trim() !== "";
    if (hasValue && !hasKey) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["specifications", "dimensions", index, "key"],
        message: "نام بعد را وارد کنید.",
      });
    }
    if (hasKey && !hasValue) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["specifications", "dimensions", index, "value"],
        message: "مقدار عددی را وارد کنید.",
      });
    }
    if (hasKey && hasValue && Number.isNaN(Number(entry.value))) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["specifications", "dimensions", index, "value"],
        message: "مقدار باید عددی باشد.",
      });
    }
    if (hasKey) {
      const normalized = entry.key.toLowerCase();
      if (seen.has(normalized)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["specifications", "dimensions", index, "key"],
          message: "این بعد تکراری است.",
        });
      }
      seen.add(normalized);
    }
  });
}

export function createProductFormSchema(template?: CategorySpecTemplate | null) {
  return z
    .object({
      sku: z
        .string()
        .trim()
        .min(1, { message: "کد محصول (SKU) الزامی است." })
        .max(50, { message: "حداکثر ۵۰ کاراکتر." }),
      name: z
        .string()
        .trim()
        .min(1, { message: "نام محصول الزامی است." })
        .max(255, { message: "حداکثر ۲۵۵ کاراکتر." }),
      description: z.string().max(5000, { message: "حداکثر ۵۰۰۰ کاراکتر." }),
      category_id: z.string().min(1, { message: "انتخاب دسته‌بندی لایه ۳ الزامی است." }),
      brand_id: z.string(),
      base_price: optionalNumberString({ min: 0 }),
      original_price: optionalNumberString({ min: 0 }),
      stock_quantity: requiredNumberString({ min: 0 }),
      stock_unit: z.enum(STOCK_UNITS),
      weight_grams: optionalNumberString({ min: 0 }),
      tax_percent: requiredNumberString({ min: 0, max: 100 }),
      warranty_text: z.string().max(255, { message: "حداکثر ۲۵۵ کاراکتر." }),
      pdf_catalog_url: z
        .string()
        .refine(isBlankOrValidUrl, { message: "آدرس URL معتبر وارد کنید." }),
      is_original: z.boolean(),
      is_active: z.boolean(),
      specifications: specificationsFormSchema,
    })
    .superRefine((data, ctx) => {
      validateKeyValueRows(data.specifications.technical_specs, "technical_specs", ctx);
      validateDimensionRows(data.specifications.dimensions, ctx);

      if (template) {
        for (const feature of template.features) {
          if (!feature.detail) continue;
          const enabled = data.specifications.featureToggles[feature.key];
          if (!enabled) continue;

          const detailValue = data.specifications.featureDetails[feature.detail.key];
          if (feature.detail.type === "string_array") {
            const list = Array.isArray(detailValue) ? detailValue : [];
            if (list.length === 0 || list.every((item) => !item.trim())) {
              ctx.addIssue({
                code: z.ZodIssueCode.custom,
                path: ["specifications", "featureDetails", feature.detail.key],
                message: `${feature.detail.label} را وارد کنید.`,
              });
            }
          }
          if (feature.detail.type === "string") {
            const text = typeof detailValue === "string" ? detailValue.trim() : "";
            if (!text) {
              ctx.addIssue({
                code: z.ZodIssueCode.custom,
                path: ["specifications", "featureDetails", feature.detail.key],
                message: `${feature.detail.label} را وارد کنید.`,
              });
            }
          }
        }
      }
    });
}

export const productFormSchema = createProductFormSchema();

export type ProductFormValues = z.infer<typeof productFormSchema>;

export const productFormDefaults: ProductFormValues = {
  sku: "",
  name: "",
  description: "",
  category_id: "",
  brand_id: "",
  base_price: "",
  original_price: "",
  stock_quantity: "0",
  stock_unit: "piece",
  weight_grams: "",
  tax_percent: String(DEFAULT_TAX_PERCENT),
  warranty_text: "",
  pdf_catalog_url: "",
  is_original: true,
  is_active: true,
  specifications: {
    technical_specs: [{ key: "", value: "" }],
    featureToggles: {},
    featureDetails: {},
    dimensions: [{ key: "", value: "" }],
  },
};

function parseNullableNumber(value: string): number | null {
  const trimmed = value.trim();
  if (trimmed === "") return null;
  const n = Number(trimmed);
  return Number.isNaN(n) ? null : n;
}

export function buildSpecificationsPayload(
  specs: SpecificationsFormValues,
  template?: CategorySpecTemplate | null,
): Record<string, unknown> {
  const technical_specs = specs.technical_specs
    .filter((row) => row.key.trim() && row.value.trim())
    .map((row) => ({ key: row.key.trim(), value: row.value.trim() }));

  const dimensions = specs.dimensions
    .filter((row) => row.key.trim() && row.value.trim() !== "")
    .map((row) => ({
      key: row.key.trim(),
      value: Number(row.value),
    }));

  const features: Record<string, unknown> = { ...specs.featureToggles };

  if (template) {
    for (const feature of template.features) {
      features[feature.key] = Boolean(specs.featureToggles[feature.key]);
      if (feature.detail) {
        const detailKey = feature.detail.key;
        if (specs.featureToggles[feature.key]) {
          const raw = specs.featureDetails[detailKey];
          if (feature.detail.type === "string_array") {
            features[detailKey] = Array.isArray(raw)
              ? raw.map((s) => s.trim()).filter(Boolean)
              : [];
          } else {
            features[detailKey] = typeof raw === "string" ? raw.trim() : "";
          }
        } else {
          delete features[detailKey];
        }
      }
    }
  } else {
    Object.assign(features, specs.featureToggles);
    Object.entries(specs.featureDetails).forEach(([key, value]) => {
      if (Array.isArray(value) ? value.length > 0 : String(value).trim()) {
        features[key] = value;
      }
    });
  }

  return { technical_specs, features, dimensions };
}

export function toProductCreatePayload(
  values: ProductFormValues,
  template?: CategorySpecTemplate | null,
): ProductCreatePayload {
  return {
    sku: values.sku.trim().toUpperCase(),
    name: values.name.trim(),
    description: values.description?.trim() || null,
    category_id: Number(values.category_id),
    brand_id: values.brand_id ? Number(values.brand_id) : null,
    base_price: parseNullableNumber(values.base_price),
    original_price: parseNullableNumber(values.original_price),
    stock_quantity: Number(values.stock_quantity),
    stock_unit: values.stock_unit,
    weight_grams: parseNullableNumber(values.weight_grams),
    tax_percent: Number(values.tax_percent),
    warranty_text: values.warranty_text?.trim() || null,
    pdf_catalog_url: values.pdf_catalog_url?.trim() || null,
    is_original: values.is_original,
    is_active: values.is_active,
    specifications: buildSpecificationsPayload(values.specifications, template),
  };
}

export function toProductUpdatePayload(
  values: ProductFormValues,
  template?: CategorySpecTemplate | null,
): ProductUpdatePayload {
  // Backend blocks stock_quantity on PUT — inventory only via /stock/adjust.
  const created = toProductCreatePayload(values, template);
  const { stock_quantity: _ignored, ...updatePayload } = created;
  return updatePayload;
}

export function productDetailToFormValues(detail: ProductDetail): ProductFormValues {
  const specs = detail.specifications as Record<string, unknown>;
  const rawFeatures = (specs.features as Record<string, unknown>) ?? {};
  const featureToggles: Record<string, boolean> = {};
  const featureDetails: Record<string, string | string[]> = {};

  for (const [key, value] of Object.entries(rawFeatures)) {
    if (typeof value === "boolean") {
      featureToggles[key] = value;
    } else if (Array.isArray(value)) {
      featureDetails[key] = value.map(String);
    } else if (typeof value === "string") {
      featureDetails[key] = value;
    }
  }

  const technicalRaw = specs.technical_specs;
  const technical_specs = Array.isArray(technicalRaw)
    ? technicalRaw.map((row) => {
        const item = row as { key?: string; value?: string };
        return { key: String(item.key ?? ""), value: String(item.value ?? "") };
      })
    : Object.entries((technicalRaw as Record<string, string>) ?? {}).map(([key, value]) => ({
        key,
        value: String(value ?? ""),
      }));

  const dimensionsRaw = specs.dimensions;
  const dimensions = Array.isArray(dimensionsRaw)
    ? dimensionsRaw.map((row) => {
        const item = row as { key?: string; value?: number | string };
        return {
          key: String(item.key ?? ""),
          value: item.value === null || item.value === undefined ? "" : String(item.value),
        };
      })
    : Object.entries((dimensionsRaw as Record<string, number>) ?? {}).map(([key, value]) => ({
        key,
        value: String(value ?? ""),
      }));

  return {
    sku: detail.sku,
    name: detail.name,
    description: detail.description ?? "",
    category_id: detail.category_id ? String(detail.category_id) : "",
    brand_id: detail.brand_id ? String(detail.brand_id) : "",
    base_price: detail.base_price ?? "",
    original_price: detail.original_price ?? "",
    stock_quantity: detail.stock_quantity,
    stock_unit: detail.stock_unit,
    weight_grams: detail.weight_grams ?? "",
    tax_percent: detail.tax_percent,
    warranty_text: detail.warranty_text ?? "",
    pdf_catalog_url: detail.pdf_catalog_url ?? "",
    is_original: detail.is_original,
    is_active: detail.is_active,
    specifications: {
      technical_specs: technical_specs.length ? technical_specs : [{ key: "", value: "" }],
      featureToggles,
      featureDetails,
      dimensions: dimensions.length ? dimensions : [{ key: "", value: "" }],
    },
  };
}
