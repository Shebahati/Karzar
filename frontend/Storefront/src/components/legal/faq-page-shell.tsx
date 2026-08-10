import Link from "next/link";
import { Container } from "@/components/ui/container";
import { STORE_EMAIL, STORE_TELEGRAM_URL } from "@/lib/store-location";
import { cn } from "@/lib/utils";
import { FaqAccordion } from "@/components/legal/faq-accordion";
import type { FaqCategory } from "@/components/legal/faq-content";

type FaqPageShellProps = {
  eyebrow: string;
  title: string;
  intro: string;
  categories: FaqCategory[];
  updatedLabel?: string;
  sibling?: { label: string; href: string };
  className?: string;
};

/** Same layout shell as legal pages; TOC lists category titles (terms-style). */
export function FaqPageShell({
  eyebrow,
  title,
  intro,
  categories,
  updatedLabel = "به‌روزرسانی: مرداد ۱۴۰۵",
  sibling,
  className,
}: FaqPageShellProps) {
  return (
    <div
      className={cn(
        "relative overflow-x-clip bg-[hsl(0_0%_97%)]",
        className,
      )}
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_70%_45%_at_100%_0%,rgba(208,35,39,0.07),transparent_55%),radial-gradient(ellipse_50%_40%_at_0%_20%,rgba(94,95,94,0.08),transparent_50%)]"
      />

      <Container className="relative py-10 sm:py-12 lg:py-16">
        <header className="max-w-3xl">
          <span className="inline-flex items-center gap-2 text-xs font-bold tracking-tight text-primary">
            <span
              aria-hidden
              className="h-1.5 w-1.5 rounded-full bg-[#D02327]"
            />
            {eyebrow}
          </span>
          <h1 className="mt-3 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
            {title}
          </h1>
          <p className="mt-4 text-base leading-8 text-muted-foreground">{intro}</p>
          <div className="mt-6 flex flex-wrap items-center gap-x-4 gap-y-2 border-y border-steel/10 py-3 text-xs font-medium text-steel">
            <span>{updatedLabel}</span>
            {sibling ? (
              <>
                <span aria-hidden className="hidden h-3 w-px bg-steel/20 sm:block" />
                <Link
                  href={sibling.href}
                  className="text-foreground transition-colors hover:text-primary"
                >
                  {sibling.label}
                </Link>
              </>
            ) : null}
            <span aria-hidden className="hidden h-3 w-px bg-steel/20 sm:block" />
            <Link
              href="/contact"
              className="text-foreground transition-colors hover:text-primary"
            >
              تماس با ما
            </Link>
          </div>
        </header>

        <div className="mt-10 grid gap-10 lg:grid-cols-[minmax(0,14rem)_minmax(0,1fr)] lg:gap-14">
          <nav aria-label="فهرست موضوعات" className="hidden lg:block">
            <div className="sticky top-24 space-y-1">
              <p className="mb-3 text-[11px] font-bold tracking-normal text-steel">
                فهرست مطالب
              </p>
              <ol className="space-y-0.5 border-s border-steel/15 ps-3">
                {categories.map((category, i) => (
                  <li key={category.id}>
                    <a
                      href={`#${category.id}`}
                      className="group flex gap-2 py-1.5 text-[13px] leading-snug text-muted-foreground transition-colors hover:text-primary"
                    >
                      <span className="tnum shrink-0 font-bold text-steel/50 group-hover:text-primary/70">
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      <span>{category.title}</span>
                    </a>
                  </li>
                ))}
              </ol>
            </div>
          </nav>

          <div className="min-w-0 space-y-8">
            <div className="no-scrollbar h-scroll flex gap-2 pb-1 lg:hidden">
              {categories.map((category) => (
                <a
                  key={category.id}
                  href={`#${category.id}`}
                  className="shrink-0 rounded-lg bg-card px-3 py-2 text-[12px] font-bold text-foreground shadow-soft ring-1 ring-inset ring-border/60"
                >
                  {category.title}
                </a>
              ))}
            </div>

            <FaqAccordion categories={categories} />

            <aside className="rounded-2xl bg-gradient-to-l from-[#D02327]/[0.08] via-card to-card p-5 ring-1 ring-inset ring-primary/10 sm:p-7">
              <h2 className="text-base font-bold text-foreground">پاسخ را پیدا نکردید؟</h2>
              <p className="mt-2 text-sm leading-7 text-muted-foreground">
                برای پیگیری سفارش، استعلام سازمانی یا ابهام در شرایط خرید با پشتیبانی در ارتباط باشید.
              </p>
              <div className="mt-4 flex flex-wrap gap-3">
                <a
                  href={`mailto:${STORE_EMAIL}`}
                  className="inline-flex min-h-10 items-center rounded-xl bg-[#D02327] px-4 text-sm font-bold text-white transition hover:bg-[#B01E22]"
                >
                  {STORE_EMAIL}
                </a>
                <a
                  href={STORE_TELEGRAM_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex min-h-10 items-center rounded-xl bg-card px-4 text-sm font-bold text-foreground shadow-soft ring-1 ring-inset ring-border/70 transition hover:text-primary"
                >
                  پشتیبانی تلگرام
                </a>
                <Link
                  href="/contact"
                  className="inline-flex min-h-10 items-center rounded-xl px-4 text-sm font-bold text-steel transition hover:text-primary"
                >
                  صفحه تماس
                </Link>
              </div>
            </aside>
          </div>
        </div>
      </Container>
    </div>
  );
}
