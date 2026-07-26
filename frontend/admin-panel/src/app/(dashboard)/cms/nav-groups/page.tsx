"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { Skeleton } from "@/components/ui/skeleton";

/**
 * Legacy CMS route — megamenu groups now live under catalog categories.
 * Keep this path so old bookmarks/nav entries redirect cleanly.
 */
export default function NavGroupsPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/catalog/categories");
  }, [router]);

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-4 py-10">
      <Skeleton className="h-10 w-64" />
      <Skeleton className="h-40 w-full" />
      <p className="text-sm text-muted-foreground">در حال انتقال به بخش دسته‌بندی‌ها…</p>
    </div>
  );
}
