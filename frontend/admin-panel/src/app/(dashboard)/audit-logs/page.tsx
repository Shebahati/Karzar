"use client";

import { Suspense } from "react";

import { Skeleton } from "@/components/ui/skeleton";
import { AuditLogsContent } from "./audit-logs-content";

export default function AuditLogsPage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto flex max-w-5xl flex-col gap-4">
          <Skeleton className="h-10 w-64" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      }
    >
      <AuditLogsContent />
    </Suspense>
  );
}
