import { describe, expect, it } from "vitest";
import {
  ARTICLES_PAGE_SIZE,
  articleCategory,
  groupArticlesByCategory,
  paginateArticles,
  sortArticlesByNewest,
  sortArticlesByViews,
} from "@/lib/articles";
import type { Article } from "@/types/content";

const base = (partial: Partial<Article> & Pick<Article, "id" | "slug" | "title">): Article => ({
  excerpt: "",
  cover_image: "",
  published_at: "2026-01-01T00:00:00Z",
  reading_minutes: 5,
  ...partial,
});

describe("articles helpers", () => {
  it("derives category from first tag", () => {
    expect(articleCategory(base({ id: 1, slug: "a", title: "A", tags: ["دریل", "ایمنی"] }))).toBe(
      "دریل",
    );
    expect(articleCategory(base({ id: 2, slug: "b", title: "B" }))).toBeNull();
  });

  it("sorts by newest", () => {
    const sorted = sortArticlesByNewest([
      base({ id: 1, slug: "old", title: "Old", published_at: "2026-01-01T00:00:00Z" }),
      base({ id: 2, slug: "new", title: "New", published_at: "2026-06-01T00:00:00Z" }),
    ]);
    expect(sorted.map((a) => a.id)).toEqual([2, 1]);
  });

  it("only sorts by views when payload includes views", () => {
    expect(
      sortArticlesByViews([
        base({ id: 1, slug: "a", title: "A" }),
        base({ id: 2, slug: "b", title: "B" }),
      ]),
    ).toBeNull();

    const sorted = sortArticlesByViews([
      base({ id: 1, slug: "a", title: "A", views: 10 }),
      base({ id: 2, slug: "b", title: "B", views: 40 }),
    ]);
    expect(sorted?.map((a) => a.id)).toEqual([2, 1]);
  });

  it("groups by first tag", () => {
    const groups = groupArticlesByCategory([
      base({ id: 1, slug: "a", title: "A", tags: ["ایمنی"] }),
      base({ id: 2, slug: "b", title: "B", tags: ["ایمنی", "کارگاه"] }),
      base({ id: 3, slug: "c", title: "C", tags: ["دریل"] }),
      base({ id: 4, slug: "d", title: "D" }),
    ]);
    expect(groups.map((g) => g.label)).toEqual(["ایمنی", "دریل"]);
    expect(groups[0].articles).toHaveLength(2);
  });

  it("paginates with max page size", () => {
    const many = Array.from({ length: 45 }, (_, i) =>
      base({ id: i + 1, slug: `s-${i}`, title: `T${i}` }),
    );
    const page2 = paginateArticles(many, 2, ARTICLES_PAGE_SIZE);
    expect(ARTICLES_PAGE_SIZE).toBe(20);
    expect(page2.items).toHaveLength(20);
    expect(page2.totalPages).toBe(3);
    expect(page2.page).toBe(2);
    expect(page2.items[0].id).toBe(21);
  });
});
