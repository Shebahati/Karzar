/** Category types mirrored from app/schemas/category.py. */

export interface Category {
  id: number;
  name: string;
  slug?: string;
  parent_id: number | null;
}

export interface CategoryFlat extends Category {
  depth: number;
  is_leaf: boolean;
  is_selectable: boolean;
  breadcrumb: string[];
  ancestor_ids: number[];
  product_count?: number;
  icon?: string | null;
  meta_title?: string | null;
  meta_description?: string | null;
  spec_template_key?: string | null;
}

export interface CategoryTreeNode extends Category {
  subcategories: CategoryTreeNode[];
  product_count?: number;
  icon?: string | null;
}

export interface Brand {
  id: number;
  name: string;
  slug?: string;
  country?: string | null;
  logo_url?: string | null;
  product_count?: number;
}

export interface BrandCreatePayload {
  name: string;
  country?: string | null;
}

export interface BrandUpdatePayload {
  name?: string;
  country?: string | null;
}

export interface CategoryCreatePayload {
  name: string;
  parent_id?: number | null;
  icon?: string | null;
  meta_title?: string | null;
  meta_description?: string | null;
  spec_template_key?: string | null;
}

export interface CategoryUpdatePayload {
  name?: string;
  parent_id?: number | null;
  slug?: string;
  icon?: string | null;
  meta_title?: string | null;
  meta_description?: string | null;
  spec_template_key?: string | null;
}

export interface BrandDeleteResult {
  id: number;
  products_cleared: number;
}

export interface CategoryDeleteResult {
  id: number;
  products_reassigned: number;
  new_category_id: number | null;
  message: string;
}

export interface CategoryListResponse {
  data: CategoryFlat[];
}
