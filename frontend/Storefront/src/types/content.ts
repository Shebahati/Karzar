/** Storefront-specific content types (comments, articles, banners). */

export interface ProductComment {
  id: number;
  product_id: number;
  author_name: string;
  rating: number; // 1..5
  body: string;
  created_at: string;
  is_verified_buyer: boolean;
}

export interface Article {
  id: number;
  slug: string;
  title: string;
  excerpt: string;
  cover_image: string;
  published_at: string;
  reading_minutes: number;
}

/** SEO override block — stripped from visible body, used in generateMetadata. */
export type BlogMetaBlock = {
  type: "meta";
  seo_title: string;
  seo_description: string;
};

export type BlogFaqItem = { question: string; answer: string };

/** A rendered content block for the blog detail body. */
export type BlogBlock =
  | BlogMetaBlock
  | { type: "paragraph"; text: string }
  | { type: "heading"; text: string }
  | { type: "subheading"; text: string }
  | { type: "list"; items: string[]; ordered?: boolean }
  | {
      type: "table";
      headers: string[];
      rows: string[][];
      caption?: string;
    }
  | {
      type: "image";
      src: string;
      alt: string;
      caption?: string;
    }
  | {
      type: "callout";
      variant?: "tip" | "warning" | "note";
      text: string;
    }
  | { type: "faq"; items: BlogFaqItem[] };

export interface BlogPost extends Article {
  author: string;
  tags: string[];
  blocks: BlogBlock[];
  related_product_ids: number[];
}

export function extractArticleSeo(post: BlogPost): {
  seoTitle: string;
  seoDescription: string;
  bodyBlocks: BlogBlock[];
  faqItems: BlogFaqItem[];
} {
  const meta = post.blocks.find((b): b is BlogMetaBlock => b.type === "meta");
  const faq = post.blocks.find((b) => b.type === "faq");
  const bodyBlocks = post.blocks.filter((b) => b.type !== "meta");
  return {
    seoTitle: meta?.seo_title || post.title,
    seoDescription: meta?.seo_description || post.excerpt,
    bodyBlocks,
    faqItems: faq && faq.type === "faq" ? faq.items : [],
  };
}

export interface HeroSlide {
  id: number;
  title: string;
  subtitle: string;
  cta_label: string;
  cta_href: string;
  image: string;
  accent: string;
}
