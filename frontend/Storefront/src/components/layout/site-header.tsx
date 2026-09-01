"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Buy, Category, Search, User } from "react-iconly";
import { Logo } from "@/components/layout/logo";
import { MegaMenu } from "@/components/layout/mega-menu";
import { SpotlightSearch } from "@/components/layout/spotlight-search";
import { Button } from "@/components/ui/button";
import { isLoggedIn } from "@/lib/api-client";
import { selectCartCount, useCartStore } from "@/store/cart-store";
import { cn, formatNumber } from "@/lib/utils";
import { useMe } from "@/features/auth/queries";

const NAV_LINKS = [
  { label: "فروشگاه", href: "/catalog" },
  { label: "مجله", href: "/blog" },
  { label: "درباره ما", href: "/about" },
  { label: "تماس با ما", href: "/contact" },
];

export function SiteHeader() {
  const pathname = usePathname();
  const [megaOpen, setMegaOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [spotlightOpen, setSpotlightOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [hasToken, setHasToken] = useState(false);
  const { data: me } = useMe(mounted && hasToken);

  const cartCount = useCartStore(selectCartCount);

  const isHome = pathname === "/";
  const overHero = isHome && !scrolled;

  useEffect(() => {
    setMounted(true);
    const sync = () => setHasToken(isLoggedIn());
    sync();
    window.addEventListener("storage", sync);
    window.addEventListener("karzar-auth-change", sync);
    return () => {
      window.removeEventListener("storage", sync);
      window.removeEventListener("karzar-auth-change", sync);
    };
  }, []);

  useEffect(() => {
    let raf = 0;
    const onScroll = () => {
      if (raf) return;
      raf = requestAnimationFrame(() => {
        raf = 0;
        setScrolled(window.scrollY > 12);
      });
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      if (raf) cancelAnimationFrame(raf);
    };
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setSpotlightOpen(true);
        setMegaOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    setSpotlightOpen(false);
  }, [pathname]);

  const displayName = me?.full_name?.trim() || me?.phone || "حساب من";
  const logoTone = overHero ? "onDark" : "brand";

  return (
    <>
      <header
        className={cn(
          "z-50 pt-[env(safe-area-inset-top,0px)] transition-[background-color,box-shadow,backdrop-filter,color] duration-300",
          /* Home: fixed overlay — never participates in document flow / height. */
          isHome ? "fixed inset-x-0 top-0" : "sticky top-0",
          scrolled
            ? "bg-white/[0.92] shadow-glass max-md:bg-white md:bg-white/70 md:backdrop-blur-xl"
            : "bg-transparent",
        )}
        onMouseLeave={() => setMegaOpen(false)}
      >
        {overHero && (
          <div
            aria-hidden
            className="pointer-events-none absolute inset-x-0 top-0 h-[6.5rem] bg-gradient-to-b from-black/55 via-black/25 to-transparent"
          />
        )}

        <div className="relative mx-auto max-w-[1280px] px-3 sm:px-4 lg:px-4 xl:px-6">
          {/* Desktop — 1fr | auto | 1fr keeps nav capsule at true viewport center */}
          <div className="hidden items-center py-2.5 lg:grid lg:grid-cols-[1fr_auto_1fr] lg:gap-2">
            <div className="flex items-center gap-2 justify-self-start">
              <Logo variant="mark" height={22} priority tone={logoTone} />
            </div>

            <nav className="justify-self-center">
              <div
                className={cn(
                  "flex items-center gap-0.5 rounded-full px-1.5 py-1 transition-colors",
                  overHero
                    ? "bg-black/40 shadow-[0_8px_32px_rgba(0,0,0,0.35)] backdrop-blur-xl"
                    : scrolled
                      ? "bg-white/55"
                      : "bg-white/45 backdrop-blur-md",
                )}
              >
                <button
                  type="button"
                  id="karzar-mega-menu-trigger"
                  aria-expanded={megaOpen}
                  aria-controls="karzar-mega-menu"
                  aria-haspopup="true"
                  onMouseEnter={() => setMegaOpen(true)}
                  onClick={() => setMegaOpen((v) => !v)}
                  className={cn(
                    "flex items-center gap-1.5 rounded-full px-3.5 py-2 text-sm font-bold transition-colors",
                    megaOpen
                      ? "bg-primary text-white"
                      : overHero
                        ? "text-white/90 hover-fine:bg-white/15 hover-fine:text-white"
                        : "text-foreground/85 hover-fine:bg-steel/[0.08] hover-fine:text-foreground",
                  )}
                >
                  <Category size="small" set="bold" />
                  دسته‌ها
                </button>
                {NAV_LINKS.map((link) => {
                  const active =
                    pathname === link.href || pathname.startsWith(link.href + "/");
                  return (
                    <Link
                      key={link.href}
                      href={link.href}
                      onMouseEnter={() => setMegaOpen(false)}
                      className={cn(
                        "rounded-full px-3.5 py-2 text-sm font-bold transition-colors",
                        overHero
                          ? active
                            ? "bg-white/15 text-white"
                            : "text-white/80 hover-fine:bg-white/12 hover-fine:text-white"
                          : active
                            ? "text-primary"
                            : "text-foreground/75 hover-fine:bg-steel/[0.08] hover-fine:text-foreground",
                      )}
                    >
                      {link.label}
                    </Link>
                  );
                })}
              </div>
            </nav>

            <div className="flex min-w-0 items-center justify-end gap-1.5 justify-self-end">
              <button
                type="button"
                onClick={() => {
                  setMegaOpen(false);
                  setSpotlightOpen(true);
                }}
                className={cn(
                  "me-1 flex h-9 items-center gap-2 rounded-full px-3 text-[13px] transition-[background-color,color,box-shadow] duration-200",
                  overHero
                    ? "bg-black/40 text-white/75 shadow-[0_8px_28px_rgba(0,0,0,0.28)] backdrop-blur-xl hover-fine:bg-black/50 hover-fine:text-white"
                    : "bg-white/80 text-steel shadow-btn-rest backdrop-blur-md hover-fine:bg-karzar-50 hover-fine:text-foreground hover-fine:shadow-btn-soft",
                )}
                aria-label="جستجو"
              >
                <Search size="small" set="bold" />
                <span className="hidden min-w-[5.5rem] text-start xl:inline">جستجوی ابزار…</span>
                <kbd
                  className={cn(
                    "ms-0.5 hidden rounded-md px-1.5 py-0.5 text-[10px] font-bold xl:inline",
                    overHero ? "bg-white/15 text-white/55" : "bg-steel/10 text-steel/60",
                  )}
                >
                  ⌘K
                </kbd>
              </button>

              <HeaderIcon href="/cart" label="سبد" count={mounted ? cartCount : 0} onDark={overHero}>
                <Buy set="bold" />
              </HeaderIcon>

              {mounted && hasToken ? (
                <Link
                  href="/account"
                  aria-label="حساب کاربری"
                  className={cn(
                    "ms-1 inline-flex max-w-[150px] items-center gap-2 rounded-full px-3 py-1.5 text-sm font-bold backdrop-blur-md transition-[background-color,color,box-shadow] duration-200",
                    overHero
                      ? "bg-black/40 text-white hover-fine:bg-black/50"
                      : "bg-white/75 text-foreground hover-fine:bg-karzar-50 hover-fine:shadow-btn-soft",
                  )}
                >
                  <span
                    className={cn(
                      "grid h-7 w-7 place-items-center rounded-full",
                      overHero
                        ? "bg-white/15 text-white"
                        : "bg-primary/10 text-primary",
                    )}
                  >
                    <User size="small" set="bold" />
                  </span>
                  <span className="truncate">{displayName}</span>
                </Link>
              ) : (
                <Link href="/login?next=/account" className="ms-1">
                  <Button
                    variant="soft"
                    size="sm"
                    className={cn(
                      "gap-1.5 rounded-full shadow-none ring-0",
                      overHero
                        ? "bg-black/40 text-white hover-fine:bg-black/55 hover-fine:text-white hover-fine:shadow-none hover-fine:translate-y-0"
                        : "bg-white/80 hover-fine:shadow-btn-soft",
                    )}
                  >
                    <User size="small" set="bold" />
                    ورود
                  </Button>
                </Link>
              )}
            </div>
          </div>

          {/* Mobile */}
          <div className="flex items-center gap-2 py-2.5 lg:hidden">
            <Logo variant="mark" height={19} priority tone={logoTone} />
            <button
              type="button"
              onClick={() => setSpotlightOpen(true)}
              className={cn(
                "ms-2 flex min-h-11 flex-1 items-center gap-2 rounded-full px-3.5 text-start text-sm transition-[background-color,color] duration-200",
                overHero
                  ? "bg-black/45 text-white/70 shadow-[0_6px_20px_rgba(0,0,0,0.28)]"
                  : "bg-white text-steel shadow-btn-rest ring-1 ring-inset ring-steel/10 active:bg-karzar-50",
              )}
              aria-label="جستجو"
            >
              <Search size="small" set="bold" />
              <span className="truncate">جستجوی ابزار…</span>
            </button>
            <Link
              href={mounted && hasToken ? "/account" : "/login?next=/account"}
              className={cn(
                "touch-target inline-flex shrink-0 items-center rounded-full transition-[background-color,box-shadow,color] duration-200",
                mounted && hasToken ? "h-11 w-11 justify-center" : "gap-1.5 px-2.5 py-1.5",
                overHero
                  ? "bg-black/45 text-white shadow-[0_6px_20px_rgba(0,0,0,0.28)] backdrop-blur-md active:bg-black/55"
                  : "bg-white text-foreground shadow-btn-rest ring-1 ring-inset ring-steel/10 hover-fine:bg-karzar-50 hover-fine:shadow-btn-soft motion-safe:hover-fine:-translate-y-px active:bg-karzar-50 active:shadow-btn-soft",
              )}
              aria-label={mounted && hasToken ? "حساب کاربری" : "ورود"}
            >
              {mounted && hasToken ? (
                <span
                  className={cn(
                    "grid h-7 w-7 place-items-center rounded-full",
                    overHero
                      ? "bg-white/15 text-white"
                      : "bg-primary/10 text-primary",
                  )}
                >
                  <User size="small" set="bold" />
                </span>
              ) : (
                <>
                  <span
                    className={cn(
                      "grid h-7 w-7 place-items-center rounded-full",
                      overHero
                        ? "bg-white/15 text-white"
                        : "bg-primary/10 text-primary",
                    )}
                  >
                    <User size="small" set="bold" />
                  </span>
                  <span className="text-xs font-bold">ورود</span>
                </>
              )}
            </Link>
          </div>

          <MegaMenu
            open={megaOpen}
            onNavigate={() => setMegaOpen(false)}
            onClose={() => setMegaOpen(false)}
          />
        </div>
      </header>

      <SpotlightSearch open={spotlightOpen} onClose={() => setSpotlightOpen(false)} />
    </>
  );
}

function HeaderIcon({
  href,
  label,
  count,
  children,
  onDark = false,
}: {
  href: string;
  label: string;
  count: number;
  children: React.ReactNode;
  onDark?: boolean;
}) {
  return (
    <Link
      href={href}
      aria-label={label}
      className={cn(
        "relative grid h-10 w-10 place-items-center rounded-full transition-colors duration-200",
        onDark
          ? "text-white hover-fine:bg-white/15 hover-fine:text-white active:bg-white/15"
          : "text-steel hover-fine:bg-steel/[0.1] hover-fine:text-foreground active:bg-steel/[0.1]",
      )}
    >
      {children}
      {count > 0 && (
        <span className="absolute -top-0.5 end-0 grid h-4 min-w-4 place-items-center rounded-full bg-primary px-1 text-[10px] font-medium text-white tnum">
          {formatNumber(count)}
        </span>
      )}
    </Link>
  );
}
