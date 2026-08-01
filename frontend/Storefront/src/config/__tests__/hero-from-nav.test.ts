import { describe, expect, it } from "vitest";
import {
  buildHeroSlidesFromNavGroups,
  matchCmsSlideToGroup,
} from "@/config/hero-from-nav";
import { NAV_GROUPS } from "@/config/nav-groups";
import type { HeroSlide } from "@/types/content";

const roots = [
  {
    id: 7,
    name: "اندازه گیری",
    slug: "andaze-giri-7",
    product_count: 10,
    image_url: "/uploads/categories/metrology.jpg",
    subcategories: [],
  },
  {
    id: 3,
    name: "اینسرت",
    slug: "insert-3",
    product_count: 5,
    image_url: "/uploads/categories/insert.jpg",
    subcategories: [],
  },
  {
    id: 5,
    name: "مته",
    slug: "mete-5",
    product_count: 2,
    image_url: null,
    subcategories: [],
  },
  {
    id: 1,
    name: "ابزارگیر",
    slug: "abzargir-1",
    product_count: 3,
    image_url: "/uploads/categories/holder.jpg",
    subcategories: [],
  },
  {
    id: 9,
    name: "دستگاه‌های صنعتی",
    slug: "machines-9",
    product_count: 1,
    image_url: null,
    subcategories: [],
  },
];

describe("hero-from-nav", () => {
  it("builds one slide per non-empty megamenu group", () => {
    const slides = buildHeroSlidesFromNavGroups(roots, NAV_GROUPS, []);
    expect(slides.map((s) => s.title)).toEqual([
      "اندازه‌گیری",
      "براده‌برداری",
      "ابزارگیری و گیرش",
      "ماشین‌ها و تجهیزات",
    ]);
    // Curated hero art wins over category packshots (full-bleed RTL composition).
    expect(slides[0].image).toBe("/images/hero/hero-metrology-left.jpg");
    expect(slides[0].cta_href).toBe("/categories/andaze-giri-7");
    // Multi-root cutting group → first root category page (single-select catalog)
    expect(slides[1].cta_href).toBe("/categories/insert-3");
    expect(slides[1].image).toBe("/images/hero/hero-cutting-left.jpg");
    expect(slides[3].image).toBe("/images/hero/hero-machines-left.jpg");
  });

  it("applies matching CMS overrides without duplicating slides", () => {
    const cms: HeroSlide[] = [
      {
        id: 42,
        title: "اندازه‌گیری دقیق کارزار",
        subtitle: "کپی سفارشی CMS",
        cta_label: "شروع خرید",
        cta_href: "/categories/andaze-giri-7",
        image: "/images/hero/cms-metrology.jpg",
        accent: "#D02327",
      },
    ];
    const slides = buildHeroSlidesFromNavGroups(roots, NAV_GROUPS, cms);
    expect(slides[0].id).toBe(42);
    expect(slides[0].subtitle).toBe("کپی سفارشی CMS");
    expect(slides[0].image).toBe("/images/hero/cms-metrology.jpg");
    expect(slides).toHaveLength(4);
  });

  it("matches CMS slides by group label", () => {
    const used = new Set<number>();
    const hit = matchCmsSlideToGroup(
      [
        {
          id: 1,
          title: "براده‌برداری",
          subtitle: "x",
          cta_label: "y",
          cta_href: "/catalog",
          image: "/a.jpg",
          accent: "#D02327",
        },
      ],
      "cutting",
      "براده‌برداری",
      used,
    );
    expect(hit?.id).toBe(1);
  });
});
