/** Spec template types for dynamic product information forms. */

export interface FeatureDetailTemplate {
  key: string;
  label: string;
  type: "string_array" | "string";
  placeholder?: string;
}

export interface FeatureTemplate {
  key: string;
  label: string;
  type: "boolean";
  detail?: FeatureDetailTemplate;
}

export interface TechnicalSpecsTemplate {
  suggested_keys: string[];
  value_options: Record<string, string[]>;
}

export interface DimensionsTemplate {
  suggested_keys: string[];
}

export interface SpecTemplateDefaultValues {
  technical_specs: { key: string; value: string }[];
  features: Record<string, boolean | string | string[]>;
  dimensions: { key: string; value: number | null }[];
}

export interface CategorySpecTemplate {
  category_id: number;
  category_name: string;
  breadcrumb: string[];
  technical_specs: TechnicalSpecsTemplate;
  features: FeatureTemplate[];
  dimensions: DimensionsTemplate;
  default_values: SpecTemplateDefaultValues;
}
