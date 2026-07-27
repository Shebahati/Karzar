import Link from "next/link";
import { categoryHref } from "@/config/nav-groups";
import { formatNumber } from "@/lib/utils";
import type { CategoryFlat } from "@/types/category";

/**
 * Hub IA drill-down: always-visible child chips (even without SEO intro).
 * Empty Persian copy when the hub has no browsable children.
 */
export function HubChildNav({
  childCategories,
  hubName,
}: {
  childCategories: CategoryFlat[];
  hubName: string;
}) {
  const browsable = childCategories
    .filter((c) => Boolean(c.slug) && (c.product_count ?? 0) > 0)
    .sort((a, b) => (b.product_count ?? 0) - (a.product_count ?? 0));

  if (browsable.length === 0) {
    if (childCategories.length === 0) return null;
    return (
      <p className="mb-4 text-sm text-muted-foreground" dir="rtl" role="status">
        زیر‌دسته‌ای با موجودی برای «{hubName}» نمایش داده نمی‌شود؛ محصولات همین شاخه را در
        فهرست زیر ببینید.
      </p>
    );
  }

  return (
    <nav aria-label="زیر‌دسته‌ها" className="mb-6" dir="rtl">
      <p className="mb-2 text-xs font-bold text-muted-foreground">زیر‌دسته‌ها</p>
      <ul className="flex gap-2 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden sm:flex-wrap sm:overflow-visible">
        {browsable.map((child) => (
          <li key={child.id} className="shrink-0">
            <Link
              href={categoryHref(child)}
              className="inline-flex min-h-10 items-center gap-2 rounded-xl bg-card px-3.5 text-sm font-medium text-foreground shadow-soft ring-1 ring-inset ring-border/60 transition hover:ring-primary/40 hover:text-primary"
            >
              <span>{child.name}</span>
              {typeof child.product_count === "number" ? (
                <span className="text-[11px] font-bold text-primary tnum">
                  {formatNumber(child.product_count)}
                </span>
              ) : null}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
