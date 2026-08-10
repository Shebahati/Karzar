"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Buy, Call, Category, Document, Home } from "react-iconly";
import { cn, formatNumber } from "@/lib/utils";
import { selectCartCount, useCartStore } from "@/store/cart-store";

/** Glassmorphism bottom navigation for mobile/tablet viewports. */
export function MobileBottomNav() {
  const pathname = usePathname();
  const [mounted, setMounted] = useState(false);
  const cartCount = useCartStore(selectCartCount);

  useEffect(() => setMounted(true), []);

  const productsActive =
    pathname === "/categories" ||
    pathname.startsWith("/categories/") ||
    pathname.startsWith("/catalog");

  const blogActive = pathname === "/blog" || pathname.startsWith("/blog/");

  return (
    <nav className="glass-strong fixed inset-x-0 bottom-0 z-[70] border-t border-border/40 pb-[env(safe-area-inset-bottom,0px)] lg:hidden">
      <ul className="mx-auto flex h-[var(--mobile-bottom-nav-chrome)] max-w-md items-stretch justify-between px-2">
        <NavItem href="/" label="خانه" Icon={Home} active={pathname === "/"} />
        <NavItem
          href="/catalog"
          label="محصولات"
          Icon={Category}
          active={productsActive}
        />
        <NavItem
          href="/cart"
          label="سبد"
          Icon={Buy}
          active={pathname.startsWith("/cart")}
          badge={mounted ? cartCount : 0}
        />
        <NavItem
          href="/contact"
          label="تماس با ما"
          Icon={Call}
          active={pathname.startsWith("/contact")}
        />
        <NavItem
          href="/blog"
          label="مقالات"
          Icon={Document}
          active={blogActive}
        />
      </ul>
    </nav>
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
          "relative flex h-full flex-col items-center justify-center gap-0.5 text-[11px] font-medium transition-colors",
          active ? "font-bold text-primary" : "text-muted-foreground",
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
