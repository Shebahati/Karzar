"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { HubIntro } from "@/lib/hub-intros";
import { categoryHref } from "@/config/nav-groups";
import type { CategoryFlat } from "@/types/category";

type Props = {
  intro: HubIntro;
  /** Direct children of the current hub — extra internal links from live taxonomy. */
  childCategories?: CategoryFlat[];
  /** Collapse long copy behind «بیشتر…» (used at page bottom). */
  collapsible?: boolean;
};

const COLLAPSE_CHARS = 280;

/**
 * SEO-002 hub body: unique Persian intro + curated internal links.
 * Child chips are taxonomy-derived (no fabricated slugs).
 */
export function CategoryHubIntro({
  intro,
  childCategories = [],
  collapsible = false,
}: Props) {
  const [expanded, setExpanded] = useState(false);
  const children = childCategories
    .filter((c) => Boolean(c.slug) && (c.product_count ?? 0) > 0)
    .slice(0, 8);

  const { previewParagraphs, needsMore } = useMemo(() => {
    if (!collapsible) {
      return { previewParagraphs: intro.paragraphs, needsMore: false };
    }
    const full = intro.paragraphs.join("\n");
    if (full.length <= COLLAPSE_CHARS && intro.paragraphs.length <= 2) {
      return { previewParagraphs: intro.paragraphs, needsMore: false };
    }
    let used = 0;
    const preview: string[] = [];
    for (const paragraph of intro.paragraphs) {
      if (used >= COLLAPSE_CHARS && preview.length >= 1) break;
      if (used + paragraph.length <= COLLAPSE_CHARS || preview.length === 0) {
        preview.push(paragraph);
        used += paragraph.length;
      } else {
        const remain = Math.max(80, COLLAPSE_CHARS - used);
        preview.push(`${paragraph.slice(0, remain).trimEnd()}…`);
        used = COLLAPSE_CHARS;
        break;
      }
    }
    return { previewParagraphs: preview, needsMore: true };
  }, [collapsible, intro.paragraphs]);

  const paragraphs = expanded || !collapsible ? intro.paragraphs : previewParagraphs;

  return (
    <section
      className="max-w-3xl space-y-4"
      aria-label={`معرفی دسته ${intro.name}`}
      dir="rtl"
    >
      <div className="space-y-3 text-sm leading-8 text-foreground/90 sm:text-[15px] sm:leading-9">
        {paragraphs.map((paragraph, index) => (
          <p key={index}>{paragraph}</p>
        ))}
      </div>

      {needsMore ? (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="text-sm font-bold text-primary underline-offset-4 hover:underline"
        >
          {expanded ? "بستن" : "بیشتر …"}
        </button>
      ) : null}

      {(expanded || !collapsible || !needsMore) && (
        <>
          <nav aria-label="لینک‌های مرتبط" className="pt-1">
            <p className="text-xs font-bold text-muted-foreground">مسیرهای مرتبط</p>
            <ul className="mt-2 flex flex-wrap gap-x-3 gap-y-2 text-sm">
              {intro.links.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="font-bold text-primary underline-offset-4 hover:underline"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>

          {children.length > 0 ? (
            <nav aria-label="زیر‌دسته‌ها" className="pt-1">
              <p className="text-xs font-bold text-muted-foreground">زیر‌دسته‌ها</p>
              <ul className="mt-2 flex flex-wrap gap-2">
                {children.map((child) => (
                  <li key={child.id}>
                    <Link
                      href={categoryHref(child)}
                      className="inline-block border-b border-border/60 pb-0.5 text-sm text-foreground/90 transition hover:border-primary hover:text-primary"
                    >
                      {child.name}
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
          ) : null}
        </>
      )}
    </section>
  );
}
