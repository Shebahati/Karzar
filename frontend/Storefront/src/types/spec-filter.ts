/** Category spec filter options from GET /categories/{id}/spec-filter-options */

export interface SpecFilterOptions {
  category_id: number;
  category_name: string;
  technical_specs: Record<string, string[]>;
}

export type SpecFilterParams = Record<string, string>;
