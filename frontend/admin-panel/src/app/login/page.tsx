"use client";

import { Suspense } from "react";
import { LoginForm } from "./login-form";
import { Skeleton } from "@/components/ui/skeleton";

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center p-8">
          <Skeleton className="h-96 w-full max-w-md" />
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
