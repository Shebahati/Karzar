/** Category & brand types mirrored from app/schemas/category.py. */

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
  /** Storefront-only presentation helpers. */
  icon?: string;
  product_count?: number;
  meta_title?: string | null;
  meta_description?: string | null;
  spec_template_key?: string | null;
}

export interface CategoryTreeNode extends Category {
  icon?: string;
  product_count?: number;
  subcategories: CategoryTreeNode[];
}

export interface Brand {
  id: number;
  name: string;
  slug?: string;
  country?: string | null;
  logo_url?: string | null;
  product_count?: number;
}
