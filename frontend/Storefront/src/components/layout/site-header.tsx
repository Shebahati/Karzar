"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Buy, Category, Document, Search, User } from "react-iconly";
import { Logo } from "@/components/layout/logo";
import { MegaMenu } from "@/components/layout/mega-menu";
import { Button } from "@/components/ui/button";
import { isLoggedIn } from "@/lib/api-client";
import {
  selectCartCount,
  selectQuoteCount,
  useCartStore,
} from "@/store/cart-store";
import { cn, formatNumber, toEnglishDigits } from "@/lib/utils";
import { useMe } from "@/features/auth/queries";

const NAV_LINKS = [
  { label: "فروشگاه", href: "/catalog" },
  { label: "مجله", href: "/blog" },
  { label: "درباره", href: "/about" },
  { label: "تماس", href: "/contact" },
];

export function SiteHeader() {
  const router = useRouter();
  const pathname = usePathname();
  const [megaOpen, setMegaOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [search, setSearch] = useState("");
  const [mobileSearchOpen, setMobileSearchOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [hasToken, setHasToken] = useState(false);
  const { data: me } = useMe(mounted && hasToken);

  const cartCount = useCartStore(selectCartCount);
  const quoteCount = useCartStore(selectQuoteCount);

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
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const submitSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const q = toEnglishDigits(search).trim();
    if (pathname === "/catalog") {
      const next = new URLSearchParams(
        typeof window !== "undefined" ? window.location.search : "",
      );
      if (q) next.set("search", q);
      else next.delete("search");
      const qs = next.toString();
      router.push(qs ? `/catalog?${qs}` : "/catalog");
      return;
    }
    router.push(q ? `/catalog?search=${encodeURIComponent(q)}` : "/catalog");
  };

  const displayName = me?.full_name?.trim() || me?.phone || "حساب من";

  return (
    <>
      <header
        className={cn(
          "sticky top-0 z-50 pt-[env(safe-area-inset-top,0px)] transition-[background,box-shadow,border-color] duration-300",
          scrolled
            ? "border-b border-white/40 bg-white/70 shadow-glass backdrop-blur-xl"
            : "border-b border-transparent bg-transparent",
        )}
        onMouseLeave={() => setMegaOpen(false)}
      >
        <div className="relative mx-auto max-w-[1280px] px-4 sm:px-6 lg:px-8">
          {/* Desktop floating center composition */}
          <div className="hidden items-center gap-4 py-3 lg:grid lg:grid-cols-[1fr_auto_1fr]">
            <div className="flex items-center gap-2 justify-self-start">
              <Logo variant="mark" height={30} priority />
            </div>

            <nav className="justify-self-center">
              <div
                className={cn(
                  "flex items-center gap-0.5 rounded-full px-1.5 py-1 transition-colors",
                  scrolled ? "bg-white/50" : "bg-white/40 backdrop-blur-md",
                )}
              >
                <button
                  type="button"
                  onMouseEnter={() => setMegaOpen(true)}
                  onClick={() => setMegaOpen((v) => !v)}
                  className={cn(
                    "flex items-center gap-1.5 rounded-full px-3.5 py-2 text-sm font-bold transition-colors",
                    megaOpen
                      ? "bg-steel text-white"
                      : "text-foreground/85 hover:bg-white/80 hover:text-foreground",
                  )}
                >
                  <Category size="small" set="bold" />
                  دسته‌ها
                </button>
                {NAV_LINKS.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    onMouseEnter={() => setMegaOpen(false)}
                    className={cn(
                      "rounded-full px-3.5 py-2 text-sm font-bold transition-colors",
                      pathname === link.href || pathname.startsWith(link.href + "/")
                        ? "text-primary"
                        : "text-foreground/75 hover:bg-white/80 hover:text-foreground",
                    )}
                  >
                    {link.label}
                  </Link>
                ))}
              </div>
            </nav>

            <div className="flex items-center justify-end gap-1.5 justify-self-end">
              <form onSubmit={submitSearch} className="relative me-1 hidden xl:block">
                <span className="pointer-events-none absolute start-3 top-1/2 -translate-y-1/2 text-steel">
                  <Search size="small" set="light" />
                </span>
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="جستجو…"
                  className={cn(
                    "h-10 w-48 rounded-full border border-border/40 bg-white/70 pe-3 ps-9 text-sm outline-none backdrop-blur-md transition-all placeholder:text-steel/60 focus:w-64 focus:ring-2 focus:ring-steel/20",
                  )}
                />
              </form>

              <HeaderIcon href="/cart" label="سبد" count={mounted ? cartCount : 0}>
                <Buy set="bold" />
              </HeaderIcon>
              <HeaderIcon href="/quote" label="استعلام" count={mounted ? quoteCount : 0} tone="steel">
                <Document set="bold" />
              </HeaderIcon>

              {mounted && hasToken ? (
                <Link
                  href="/account"
                  className="ms-1 inline-flex max-w-[150px] items-center gap-2 rounded-full border border-border/40 bg-white/70 px-3 py-1.5 text-sm font-bold text-foreground backdrop-blur-md hover:border-steel/30"
                >
                  <span className="grid h-7 w-7 place-items-center rounded-full bg-steel text-[11px] text-white">
                    {(displayName || "ک").slice(0, 1)}
                  </span>
                  <span className="truncate">{displayName}</span>
                </Link>
              ) : (
                <Link href="/login?next=/account" className="ms-1">
                  <Button
                    variant="soft"
                    size="sm"
                    className="gap-1.5 rounded-full border border-border/40 bg-white/70"
                  >
                    <User size="small" set="bold" />
                    ورود
                  </Button>
                </Link>
              )}
            </div>
          </div>

          {/* Mobile / tablet bar */}
          <div className="flex items-center gap-2 py-3 lg:hidden">
            <Logo variant="mark" height={26} priority />
            <div className="ms-auto flex items-center gap-1">
              <button
                type="button"
                className="touch-target rounded-full text-steel hover:bg-white/60"
                aria-label="جستجو"
                onClick={() => setMobileSearchOpen((v) => !v)}
              >
                <Search set="bold" />
              </button>
              {mounted && hasToken ? (
                <Link
                  href="/account"
                  className="touch-target grid place-items-center rounded-full text-steel hover:bg-white/60"
                  aria-label="حساب کاربری"
                >
                  <User set="bold" />
                </Link>
              ) : (
                <Link
                  href="/login?next=/account"
                  className="touch-target grid place-items-center rounded-full text-steel hover:bg-white/60"
                  aria-label="ورود"
                >
                  <User set="bold" />
                </Link>
              )}
            </div>
          </div>

          {mobileSearchOpen && (
            <form
              onSubmit={(e) => {
                submitSearch(e);
                setMobileSearchOpen(false);
              }}
              className="pb-3 lg:hidden"
            >
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                autoFocus
                placeholder="جستجوی محصول…"
                className="h-12 w-full rounded-2xl border border-border/50 bg-white/80 px-4 text-base outline-none backdrop-blur-md focus:ring-2 focus:ring-steel/20"
              />
            </form>
          )}

          <MegaMenu
            open={megaOpen}
            onNavigate={() => setMegaOpen(false)}
            onClose={() => setMegaOpen(false)}
          />
        </div>
      </header>
    </>
  );
}

function HeaderIcon({
  href,
  label,
  count,
  children,
  tone = "primary",
}: {
  href: string;
  label: string;
  count: number;
  children: React.ReactNode;
  tone?: "primary" | "steel";
}) {
  return (
    <Link
      href={href}
      aria-label={label}
      className="relative grid h-10 w-10 place-items-center rounded-full text-steel transition-colors hover:bg-white/70 hover:text-foreground"
    >
      {children}
      {count > 0 && (
        <span
          className={cn(
            "absolute -top-0.5 end-0 grid h-4 min-w-4 place-items-center rounded-full px-1 text-[10px] font-medium text-white tnum",
            tone === "steel" ? "bg-steel" : "bg-primary",
          )}
        >
          {formatNumber(count)}
        </span>
      )}
    </Link>
  );
}
