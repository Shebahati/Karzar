/** CMS admin types — aligned with app/schemas/cms.py + mock-api. */

import type { PaginatedResponse } from "./common";

export const ARTICLE_BLOCK_TYPES = [
  "paragraph",
  "heading",
  "subheading",
  "list",
  "quote",
  "image",
  "table",
  "callout",
  "faq",
  "meta",
] as const;
export type ArticleBlockType = (typeof ARTICLE_BLOCK_TYPES)[number];

export const ARTICLE_BLOCK_TYPE_LABELS: Record<ArticleBlockType, string> = {
  paragraph: "پاراگراف",
  heading: "عنوان",
  subheading: "زیرعنوان",
  list: "فهرست",
  quote: "نقل‌قول",
  image: "تصویر",
  table: "جدول",
  callout: "نکته",
  faq: "سوالات متداول",
  meta: "سئو",
};

export interface ArticleBlock {
  type: ArticleBlockType;
  text?: string;
  items?: string[];
}

export interface Article {
  id: number;
  slug: string;
  title: string;
  excerpt: string;
  cover_image: string | null;
  published_at: string;
  reading_minutes: number;
  author: string;
  tags: string[];
  related_product_ids: number[];
  blocks: ArticleBlock[];
  is_published: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface ArticleCreatePayload {
  slug: string;
  title: string;
  excerpt: string;
  cover_image?: string | null;
  published_at: string;
  reading_minutes: number;
  author: string;
  tags?: string[];
  related_product_ids?: number[];
  blocks?: ArticleBlock[];
  is_published: boolean;
}

export type ArticleUpdatePayload = Partial<ArticleCreatePayload>;

export interface ArticleListParams {
  skip?: number;
  limit?: number;
  search?: string;
  is_published?: boolean;
}

export type ArticleListResponse = PaginatedResponse<Article>;

export interface HeroSlide {
  id: number;
  title: string;
  subtitle: string | null;
  cta_label: string | null;
  cta_href: string | null;
  image: string;
  accent: string;
  sort_order: number;
  is_active: boolean;
}

export interface HeroSlideCreatePayload {
  title: string;
  subtitle?: string | null;
  cta_label?: string | null;
  cta_href?: string | null;
  image: string;
  accent: string;
  sort_order: number;
  is_active: boolean;
}

export type HeroSlideUpdatePayload = Partial<HeroSlideCreatePayload>;

export interface HeroSlideListParams {
  skip?: number;
  limit?: number;
  is_active?: boolean;
}

export type HeroSlideListResponse = PaginatedResponse<HeroSlide>;

export interface ProductComment {
  id: number;
  product_id: number;
  author_name: string;
  rating: number;
  body: string;
  created_at: string;
  is_verified_buyer: boolean;
}

export interface ProductCommentListParams {
  skip?: number;
  limit?: number;
  product_id?: number;
}

export type ProductCommentListResponse = PaginatedResponse<ProductComment>;

export interface ContactSubmission {
  id: number;
  ticket_code: string;
  full_name: string;
  phone: string;
  subject: string;
  message: string;
  created_at: string;
}

export interface ContactSubmissionListParams {
  skip?: number;
  limit?: number;
  search?: string;
  phone?: string;
}

export type ContactSubmissionListResponse = PaginatedResponse<ContactSubmission>;

/** Aliases used by earlier integration pages */
export type CmsArticle = Article;
export type CmsArticleCreatePayload = ArticleCreatePayload;
export type CmsArticleUpdatePayload = ArticleUpdatePayload;
export type CmsArticleListResponse = ArticleListResponse;
export type CmsHeroSlide = HeroSlide;
export type CmsHeroCreatePayload = HeroSlideCreatePayload;
export type CmsHeroUpdatePayload = HeroSlideUpdatePayload;
export type CmsProductComment = ProductComment;
export type CmsCommentListResponse = ProductCommentListResponse;
export type CmsContactSubmission = ContactSubmission;
export type CmsContactListResponse = ContactSubmissionListResponse;
