"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Search } from "react-iconly";
import { toast } from "sonner";

import { Input } from "@/components/ui/input";
import { catalogService } from "@/services/catalog";
import { ApiError } from "@/lib/api-client";

const ROUTE_TITLES: { prefix: string; title: string }[] = [
  { prefix: "/catalog/products/new", title: "افزودن محصول جدید" },
  { prefix: "/catalog/products/deleted", title: "محصولات حذف‌شده" },
  { prefix: "/catalog/products", title: "مدیریت محصولات" },
  { prefix: "/catalog/categories", title: "دسته‌بندی‌ها" },
  { prefix: "/orders", title: "سفارش‌ها" },
  { prefix: "/quotes", title: "استعلام‌های قیمت" },
  { prefix: "/customers", title: "مشتریان" },
  { prefix: "/audit-logs", title: "گزارش ممیزی" },
  { prefix: "/reports", title: "گزارش‌ها" },
  { prefix: "/documents", title: "اسناد" },
  { prefix: "/settings", title: "تنظیمات" },
];

function resolveTitle(pathname: string): string {
  if (pathname === "/") return "داشبورد";
  const match = ROUTE_TITLES.find((r) => pathname.startsWith(r.prefix));
  return match?.title ?? "کارزار";
}

export function Header() {
  const router = useRouter();
  const pathname = usePathname();
  const title = resolveTitle(pathname);
  const [sku, setSku] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  async function lookupSku(value: string) {
    const trimmed = value.trim();
    if (trimmed.length < 3) return;
    try {
      const product = await catalogService.getProductBySku(trimmed);
      router.push(`/catalog/products/${product.id}/edit`);
      setSku("");
    } catch (err) {
      if (err instanceof ApiError && err.code === "NOT_FOUND") {
        toast.error("محصولی با این SKU یافت نشد");
      }
    }
  }

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  return (
    <header className="glass sticky top-0 z-30 flex h-20 items-center gap-4 px-6 lg:px-8">
      <div className="flex min-w-0 flex-col">
        <h1 className="truncate text-xl font-bold text-ink">{title}</h1>
        <p className="text-xs text-muted-foreground">پنل مدیریت فروشگاه کارزار</p>
      </div>

      <div className="relative ms-auto hidden w-72 md:block">
        <span className="pointer-events-none absolute inset-y-0 start-3 flex items-center text-muted-foreground">
          <Search set="light" size={18} />
        </span>
        <Input
          placeholder="جستجوی سریع SKU..."
          className="bg-white/60 ps-10"
          dir="ltr"
          value={sku}
          onChange={(e) => {
            const next = e.target.value;
            setSku(next);
            if (debounceRef.current) clearTimeout(debounceRef.current);
            debounceRef.current = setTimeout(() => void lookupSku(next), 350);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              if (debounceRef.current) clearTimeout(debounceRef.current);
              void lookupSku(sku);
            }
          }}
        />
      </div>

      <div className="flex items-center gap-3 rounded-xl bg-white/60 py-1.5 pe-2 ps-3 shadow-soft">
        <div className="hidden flex-col items-end leading-tight sm:flex">
          <span className="text-sm font-bold text-foreground">مدیر سیستم</span>
          <span className="text-xs text-muted-foreground">سوپر ادمین</span>
        </div>
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-sm font-bold text-primary-foreground">
          م
        </div>
      </div>
    </header>
  );
}
