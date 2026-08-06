import Link from "next/link";
import { Container } from "@/components/ui/container";
import { STORE_EMAIL, STORE_TELEGRAM_URL } from "@/lib/store-location";
import { cn } from "@/lib/utils";

export type LegalSection = {
  id: string;
  title: string;
  paragraphs: string[];
  bullets?: string[];
  /** Soft callout under the body copy */
  note?: string;
  /** Inline related links under the note / body */
  related?: { label: string; href: string }[];
};

type LegalPageShellProps = {
  eyebrow: string;
  title: string;
  intro: string;
  updatedLabel?: string;
  sections: LegalSection[];
  /** Sibling legal link shown in the header strip */
  sibling?: { label: string; href: string };
  className?: string;
};

export function LegalPageShell({
  eyebrow,
  title,
  intro,
  updatedLabel = "به‌روزرسانی: مرداد ۱۴۰۵",
  sections,
  sibling,
  className,
}: LegalPageShellProps) {
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
          <nav
            aria-label="فهرست بخش‌ها"
            className="hidden lg:block"
          >
            <div className="sticky top-24 space-y-1">
              <p className="mb-3 text-[11px] font-bold tracking-wide text-steel">
                فهرست مطالب
              </p>
              <ol className="space-y-0.5 border-s border-steel/15 ps-3">
                {sections.map((section, i) => (
                  <li key={section.id}>
                    <a
                      href={`#${section.id}`}
                      className="group flex gap-2 py-1.5 text-[13px] leading-snug text-muted-foreground transition-colors hover:text-primary"
                    >
                      <span className="tnum shrink-0 font-bold text-steel/50 group-hover:text-primary/70">
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      <span>{section.title}</span>
                    </a>
                  </li>
                ))}
              </ol>
            </div>
          </nav>

          <div className="min-w-0 space-y-8">
            {/* Mobile section chips */}
            <div className="no-scrollbar h-scroll flex gap-2 pb-1 lg:hidden">
              {sections.map((section) => (
                <a
                  key={section.id}
                  href={`#${section.id}`}
                  className="shrink-0 rounded-lg bg-card px-3 py-2 text-[12px] font-bold text-foreground shadow-soft ring-1 ring-inset ring-border/60"
                >
                  {section.title}
                </a>
              ))}
            </div>

            {sections.map((section, i) => (
              <section
                key={section.id}
                id={section.id}
                className="scroll-mt-28 rounded-2xl bg-card/80 p-5 shadow-soft ring-1 ring-inset ring-border/50 sm:p-7"
              >
                <div className="flex items-start gap-3">
                  <span
                    aria-hidden
                    className="mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[#D02327]/[0.08] text-[12px] font-bold text-primary tnum"
                  >
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <div className="min-w-0 flex-1">
                    <h2 className="text-lg font-bold tracking-tight text-foreground sm:text-xl">
                      {section.title}
                    </h2>
                    <div className="mt-3 space-y-3 text-sm leading-7 text-muted-foreground">
                      {section.paragraphs.map((p, pi) => (
                        <p key={`${section.id}-p-${pi}`}>{p}</p>
                      ))}
                      {section.bullets?.length ? (
                        <ul className="space-y-2 ps-1">
                          {section.bullets.map((b, bi) => (
                            <li
                              key={`${section.id}-b-${bi}`}
                              className="flex gap-2.5"
                            >
                              <span
                                aria-hidden
                                className="mt-2.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[#D02327]"
                              />
                              <span>{b}</span>
                            </li>
                          ))}
                        </ul>
                      ) : null}
                      {section.note ? (
                        <p className="rounded-xl bg-secondary/50 px-3.5 py-3 text-[13px] leading-6 text-foreground/80">
                          {section.note}
                        </p>
                      ) : null}
                      {section.related?.length ? (
                        <p className="flex flex-wrap gap-x-4 gap-y-1 text-[13px] font-bold">
                          {section.related.map((r) => (
                            <Link
                              key={r.href}
                              href={r.href}
                              className="text-primary transition-colors hover:underline"
                            >
                              {r.label}
                            </Link>
                          ))}
                        </p>
                      ) : null}
                    </div>
                  </div>
                </div>
              </section>
            ))}

            <aside className="rounded-2xl bg-gradient-to-l from-[#D02327]/[0.08] via-card to-card p-5 ring-1 ring-inset ring-primary/10 sm:p-7">
              <h2 className="text-base font-bold text-foreground">نیاز به توضیح بیشتر؟</h2>
              <p className="mt-2 text-sm leading-7 text-muted-foreground">
                برای پرسش‌های حقوقی، همکاری یا پیگیری سفارش با ما در ارتباط باشید.
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
