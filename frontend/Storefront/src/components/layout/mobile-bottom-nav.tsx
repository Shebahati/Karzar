"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Buy, Category, Document, Home, User } from "react-iconly";
import { MobileCategoryMenu } from "@/components/layout/mobile-category-menu";
import { cn, formatNumber } from "@/lib/utils";
import { useMe } from "@/features/auth/queries";
import { isLoggedIn } from "@/lib/api-client";
import { selectCartCount, selectQuoteCount, useCartStore } from "@/store/cart-store";

/** Glassmorphism bottom navigation for mobile/tablet viewports. */
export function MobileBottomNav() {
  const pathname = usePathname();
  const [mounted, setMounted] = useState(false);
  const [catalogOpen, setCatalogOpen] = useState(false);
  const cartCount = useCartStore(selectCartCount);
  const quoteCount = useCartStore(selectQuoteCount);
  const { data: me } = useMe(mounted && isLoggedIn());

  useEffect(() => setMounted(true), []);

  const accountHref = mounted && isLoggedIn() ? "/account" : "/login?next=/account";
  const accountLabel = me?.full_name?.split(" ")[0] ?? "حساب";

  return (
    <>
      <MobileCategoryMenu open={catalogOpen} onClose={() => setCatalogOpen(false)} />

      <nav className="glass-strong fixed inset-x-0 bottom-0 z-50 border-t border-border/40 pb-[env(safe-area-inset-bottom)] lg:hidden">
        <ul className="mx-auto flex max-w-md items-stretch justify-between px-2">
          <NavItem href="/" label="خانه" Icon={Home} active={pathname === "/"} />

          <li className="flex-1">
            <button
              type="button"
              onClick={() => setCatalogOpen(true)}
              className={cn(
                "relative flex w-full flex-col items-center gap-1 py-2.5 text-[11px] font-bold transition-colors",
                catalogOpen || pathname.startsWith("/catalog")
                  ? "text-primary"
                  : "text-muted-foreground",
              )}
            >
              <Category size="medium" set={catalogOpen ? "bold" : "light"} />
              محصولات
            </button>
          </li>

          <NavItem
            href="/cart"
            label="سبد"
            Icon={Buy}
            active={pathname.startsWith("/cart")}
            badge={mounted ? cartCount : 0}
          />
          <NavItem
            href="/quote"
            label="استعلام"
            Icon={Document}
            active={pathname.startsWith("/quote")}
            badge={mounted ? quoteCount : 0}
            badgeTone="steel"
          />
          <NavItem href={accountHref} label={accountLabel} Icon={User} active={pathname.startsWith("/account") || pathname === "/login"} />
        </ul>
      </nav>
    </>
  );
}

function NavItem({
  href,
  label,
  Icon,
  active,
  badge = 0,
  badgeTone = "primary",
}: {
  href: string;
  label: string;
  Icon: typeof Home;
  active: boolean;
  badge?: number;
  badgeTone?: "primary" | "steel";
}) {
  return (
    <li className="flex-1">
      <Link
        href={href}
        className={cn(
          "relative flex flex-col items-center gap-1 py-2.5 text-[11px] font-medium transition-colors",
          active ? "text-primary" : "text-muted-foreground",
        )}
      >
        <Icon size="medium" set={active ? "bold" : "light"} />
        {label}
        {badge > 0 && (
          <span
            className={cn(
              "absolute top-1 ms-5 grid h-4 min-w-4 place-items-center rounded-full px-1 text-[10px] text-white tnum",
              badgeTone === "steel" ? "bg-foreground/80" : "bg-primary",
            )}
          >
            {formatNumber(badge)}
          </span>
        )}
      </Link>
    </li>
  );
}
