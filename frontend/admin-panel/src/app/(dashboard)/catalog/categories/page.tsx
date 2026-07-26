"use client";

import { Suspense } from "react";

import { Skeleton } from "@/components/ui/skeleton";
import { CategoriesContent } from "./categories-content";

export default function CategoriesPage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto flex max-w-7xl flex-col gap-6">
          <Skeleton className="h-12 w-72" />
          <Skeleton className="h-10 w-80" />
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <Skeleton className="h-[420px] w-full rounded-xl" />
            <Skeleton className="h-[420px] w-full rounded-xl" />
            <Skeleton className="h-[420px] w-full rounded-xl" />
          </div>
        </div>
      }
    >
      <CategoriesContent />
    </Suspense>
  );
}
