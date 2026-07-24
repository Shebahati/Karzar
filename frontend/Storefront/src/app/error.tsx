"use client";

import { useEffect } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Container } from "@/components/ui/container";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <Container className="grid min-h-[60vh] place-items-center py-16">
      <div className="w-full max-w-md rounded-2xl bg-card p-8 text-center shadow-soft">
        <h1 className="text-xl font-bold text-foreground">خطایی رخ داد</h1>
        <p className="mt-2 text-sm leading-7 text-muted-foreground">
          بارگذاری این صفحه با مشکل مواجه شد. می‌توانید دوباره تلاش کنید یا به صفحهٔ اصلی برگردید.
        </p>
        <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-center">
          <Button type="button" onClick={reset}>
            تلاش مجدد
          </Button>
          <Link href="/">
            <Button type="button" variant="outline">
              بازگشت به خانه
            </Button>
          </Link>
        </div>
      </div>
    </Container>
  );
}
