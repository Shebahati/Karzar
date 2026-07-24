"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Buy, Category, Document, Search, User } from "react-iconly";
import { Logo } from "@/components/layout/logo";
import { MegaMenu } from "@/components/layout/mega-menu";
import { Button } from "@/components/ui/button";
import { authService } from "@/services/auth";
import { isLoggedIn } from "@/lib/api-client";
import {
  selectCartCount,
  selectQuoteCount,
  useCartStore,
} from "@/store/cart-store";
import { cn, formatNumber, toEnglishDigits } from "@/lib/utils";
import { useQueryClient } from "@tanstack/react-query";
import { authKeys } from "@/features/auth/queries";

const NAV_LINKS = [
  { label: "صفحه اصلی", href: "/" },
  { label: "فروشگاه", href: "/catalog" },
  { label: "مجله کارزار", href: "/blog" },
  { label: "درباره ما", href: "/about" },
  { label: "تماس با ما", href: "/contact" },
];

export function SiteHeader() {
  const router = useRouter();
  const pathname = usePathname();
  const queryClient = useQueryClient();
  const [megaOpen, setMegaOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [search, setSearch] = useState("");
  const [mobileSearchOpen, setMobileSearchOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [hasToken, setHasToken] = useState(false);

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
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const submitSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const q = toEnglishDigits(search).trim();
    // On catalog: merge search into existing filters. Elsewhere: fresh catalog search.
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

  return (
    <>
      <header
        className={cn(
          "sticky top-0 z-50 pt-[env(safe-area-inset-top,0px)] transition-shadow duration-300",
          scrolled ? "border-b border-border/60 bg-card/95 shadow-soft backdrop-blur-md" : "bg-card/90 backdrop-blur-md",
        )}
        onMouseLeave={() => setMegaOpen(false)}
      >
        <div className="relative mx-auto max-w-[1320px] px-5 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3 py-3">
            <Logo />

            <form
              onSubmit={submitSearch}
              className="relative ms-1 hidden flex-1 items-center md:flex"
            >
              <span className="pointer-events-none absolute start-4 text-muted-foreground">
                <Search size="small" set="light" />
              </span>
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="جستجوی محصول، برند یا کد کالا…"
                className="h-11 w-full rounded-xl bg-input ps-11 pe-4 text-base outline-none transition-shadow placeholder:text-muted-foreground focus:ring-2 focus:ring-ring/40 md:text-sm"
              />
            </form>

            <div className="ms-auto flex items-center gap-1">
              <button
                type="button"
                className="touch-target rounded-lg text-foreground/80 hover:bg-muted md:hidden"
                aria-label="جستجو"
                onClick={() => setMobileSearchOpen((v) => !v)}
              >
                <Search set="bold" />
              </button>

              {/* Cart / quote live in bottom nav on phones — avoid duplicate chrome. */}
              <div className="hidden items-center gap-1 md:flex">
                <HeaderIcon href="/cart" label="سبد" count={mounted ? cartCount : 0} tone="primary">
                  <Buy set="bold" />
                </HeaderIcon>
                <HeaderIcon href="/quote" label="استعلام" count={mounted ? quoteCount : 0} tone="steel">
                  <Document set="bold" />
                </HeaderIcon>
              </div>

              {mounted && hasToken ? (
                <div className="hidden items-center gap-2 sm:flex">
                  <Link href="/account">
                    <Button variant="soft" size="sm" className="max-w-[140px] gap-1.5 truncate">
                      <User size="small" set="bold" />
                      سفارش‌ها
                    </Button>
                  </Link>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-xs text-muted-foreground"
                    onClick={() => {
                      void authService.logout().then(() => {
                        void queryClient.removeQueries({ queryKey: authKeys.me });
                        setHasToken(false);
                        router.push("/");
                      });
                    }}
                  >
                    خروج
                  </Button>
                </div>
              ) : (
                <Link href="/login?next=/account" className="hidden sm:block">
                  <Button variant="soft" size="sm" className="gap-1.5">
                    <User size="small" set="bold" />
                    ورود
                  </Button>
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
              className="pb-3 md:hidden"
            >
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                autoFocus
                placeholder="جستجوی محصول…"
                className="h-12 w-full rounded-lg bg-input px-4 text-base outline-none focus:ring-2 focus:ring-ring/40"
              />
            </form>
          )}

          <nav className="hidden h-12 items-center gap-1 lg:flex">
            <button
              type="button"
              onMouseEnter={() => setMegaOpen(true)}
              onClick={() => setMegaOpen((v) => !v)}
              className={cn(
                "flex items-center gap-2 rounded-xl px-3.5 py-2 text-sm font-bold transition-colors",
                megaOpen ? "bg-accent text-primary" : "hover:bg-muted",
              )}
            >
              <Category size="small" set="bold" />
              دسته‌بندی محصولات
            </button>
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onMouseEnter={() => setMegaOpen(false)}
                className="rounded-xl px-3.5 py-2 text-sm font-bold text-foreground/80 transition-colors hover:bg-muted hover:text-foreground"
              >
                {link.label}
              </Link>
            ))}
          </nav>

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
      className="relative flex flex-col items-center gap-0.5 px-1.5 py-1 text-foreground/80 transition-colors hover:text-primary"
    >
      <span className="touch-target relative rounded-lg hover:bg-muted">
        {children}
        {count > 0 && (
          <span
            className={cn(
              "absolute -top-0.5 end-0.5 grid h-4 min-w-4 place-items-center rounded-full px-1 text-[10px] font-medium text-white tnum",
              tone === "steel" ? "bg-foreground/80" : "bg-primary",
            )}
          >
            {formatNumber(count)}
          </span>
        )}
      </span>
      <span className="hidden text-[10px] font-medium sm:block">{label}</span>
    </Link>
  );
}
