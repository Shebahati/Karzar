import Link from "next/link";
import type { HubIntro } from "@/lib/hub-intros";
import { categoryHref } from "@/config/nav-groups";
import type { CategoryFlat } from "@/types/category";

type Props = {
  intro: HubIntro;
  /** Direct children of the current hub — extra internal links from live taxonomy. */
  childCategories?: CategoryFlat[];
};

/**
 * SEO-002 hub body: unique Persian intro + curated internal links.
 * Child chips are taxonomy-derived (no fabricated slugs).
 */
export function CategoryHubIntro({ intro, childCategories = [] }: Props) {
  const children = childCategories
    .filter((c) => Boolean(c.slug) && (c.product_count ?? 0) > 0)
    .slice(0, 8);

  return (
    <section
      className="mt-5 max-w-3xl space-y-4"
      aria-label={`معرفی دسته ${intro.name}`}
      dir="rtl"
    >
      <div className="space-y-3 text-sm leading-8 text-foreground/90 sm:text-[15px] sm:leading-9">
        {intro.paragraphs.map((paragraph, index) => (
          <p key={index}>{paragraph}</p>
        ))}
      </div>

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
    </section>
  );
}
