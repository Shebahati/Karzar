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
  image_url?: string | null;
  product_count?: number;
  meta_title?: string | null;
  meta_description?: string | null;
  spec_template_key?: string | null;
  megamenu_hidden?: boolean;
  megamenu_as_leaf?: boolean;
  megamenu_bold?: boolean | null;
}

export interface CategoryTreeNode extends Category {
  icon?: string;
  image_url?: string | null;
  product_count?: number;
  megamenu_hidden?: boolean;
  megamenu_as_leaf?: boolean;
  megamenu_bold?: boolean | null;
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
