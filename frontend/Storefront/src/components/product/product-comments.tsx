"use client";

import { useEffect, useId, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Chat, ShieldDone, Star } from "react-iconly";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { useComments, catalogKeys } from "@/features/catalog/queries";
import { catalogService } from "@/services/catalog";
import { Skeleton } from "@/components/ui/skeleton";
import { Button, buttonVariants } from "@/components/ui/button";
import { Field, fieldInputClass, fieldTextareaClass } from "@/components/ui/field";
import { ApiError, isLoggedIn as checkLoggedIn } from "@/lib/api-client";
import { cn } from "@/lib/utils";

function Stars({
  rating,
  onSelect,
  size = "small",
  showValue = false,
}: {
  rating: number;
  onSelect?: (value: number) => void;
  size?: "small" | "medium";
  /** Compact selected-value label for the interactive control. */
  showValue?: boolean;
}) {
  return (
    <div
      className={cn("inline-flex items-center", onSelect ? "gap-2" : "gap-0.5")}
      role={onSelect ? "radiogroup" : "img"}
      aria-label={`${rating} از ۵`}
    >
      <div className="flex items-center gap-0.5">
        {Array.from({ length: 5 }).map((_, i) => {
          const active = i < rating;
          const common = cn(
            "transition-colors",
            active ? "text-warning" : "text-muted-foreground/30",
            onSelect &&
              "rounded-md p-1 hover-fine:text-warning focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/35",
          );
          if (!onSelect) {
            return (
              <span key={i} className={common} aria-hidden>
                <Star size={size} set={active ? "bold" : "light"} />
              </span>
            );
          }
          return (
            <button
              key={i}
              type="button"
              role="radio"
              aria-checked={i + 1 === rating}
              className={common}
              onClick={() => onSelect(i + 1)}
              aria-label={`${i + 1} ستاره`}
            >
              <Star size={size} set={active ? "bold" : "light"} />
            </button>
          );
        })}
      </div>
      {showValue && onSelect ? (
        <span className="text-xs font-bold text-muted-foreground tnum">
          {rating.toLocaleString("fa-IR")}
          <span className="font-medium text-muted-foreground/70"> / ۵</span>
        </span>
      ) : null}
    </div>
  );
}

function formatCommentDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString("fa-IR", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  } catch {
    return "";
  }
}

export function ProductComments({ productId }: { productId: number }) {
  const { data, isLoading } = useComments(productId);
  const queryClient = useQueryClient();
  const pathname = usePathname();
  const formId = useId();
  const [loggedIn, setLoggedIn] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [formSuccess, setFormSuccess] = useState<string | null>(null);

  const [authorName, setAuthorName] = useState("");
  const [rating, setRating] = useState(5);
  const [body, setBody] = useState("");

  const loginHref = `/login?next=${encodeURIComponent(pathname || "/")}`;

  useEffect(() => {
    setLoggedIn(checkLoggedIn());
    const onAuth = () => setLoggedIn(checkLoggedIn());
    window.addEventListener("karzar-auth-change", onAuth);
    return () => window.removeEventListener("karzar-auth-change", onAuth);
  }, []);

  const createComment = useMutation({
    mutationFn: () =>
      catalogService.createComment(productId, {
        author_name: authorName.trim(),
        rating,
        body: body.trim(),
      }),
    onSuccess: () => {
      setFormSuccess("دیدگاه شما دریافت شد و پس از بررسی نمایش داده می‌شود.");
      setFormError(null);
      setBody("");
      void queryClient.invalidateQueries({ queryKey: catalogKeys.comments(productId) });
    },
    onError: (err) => {
      setFormSuccess(null);
      setFormError(err instanceof ApiError ? err.message : "ثبت دیدگاه ناموفق بود.");
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setFormSuccess(null);
    if (!loggedIn) {
      setFormError("برای ثبت دیدگاه وارد حساب شوید.");
      return;
    }
    if (authorName.trim().length < 2 || body.trim().length < 3) {
      setFormError("نام و متن دیدگاه را کامل وارد کنید.");
      return;
    }
    createComment.mutate();
  }

  const avgRating =
    data && data.length
      ? data.reduce((sum, c) => sum + (c.rating ?? 0), 0) / data.length
      : null;
  const hasReviews = Boolean(data?.length);
  const reviewCount = data?.length ?? 0;

  return (
    <div className="space-y-5">
      {/* Summary + write action */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1.5">
          {avgRating != null ? (
            <>
              <div className="flex items-baseline gap-1">
                <span className="text-xl font-bold tracking-tight text-foreground tnum sm:text-2xl">
                  {avgRating.toFixed(1)}
                </span>
                <span className="text-xs text-muted-foreground sm:text-sm">از ۵</span>
              </div>
              <Stars rating={Math.round(avgRating)} size="medium" />
              <span className="text-xs text-muted-foreground tnum sm:text-sm">
                {reviewCount.toLocaleString("fa-IR")} دیدگاه
              </span>
            </>
          ) : !isLoading ? (
            <p className="text-sm text-muted-foreground">هنوز امتیازی ثبت نشده</p>
          ) : (
            <Skeleton className="h-6 w-40 rounded-lg" />
          )}
        </div>

        {hasReviews ? (
          loggedIn ? (
            <a
              href={`#${formId}`}
              className={cn(buttonVariants({ variant: "soft", size: "sm" }), "shrink-0")}
            >
              نوشتن دیدگاه
            </a>
          ) : (
            <Link
              href={loginHref}
              className={cn(buttonVariants({ variant: "soft", size: "sm" }), "shrink-0")}
            >
              ورود برای ثبت دیدگاه
            </Link>
          )
        ) : null}
      </div>

      {/* List / empty / loading */}
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 2 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full rounded-xl" />
          ))}
        </div>
      ) : !hasReviews ? (
        <div
          className="flex items-start gap-3 rounded-xl border border-dashed border-steel/15 bg-secondary/25 px-3.5 py-3.5 sm:items-center sm:px-4"
          role="status"
        >
          <span
            className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-white/80 text-muted-foreground/65"
            aria-hidden
          >
            <Chat size="small" set="light" />
          </span>
          <div className="min-w-0 pt-0.5 sm:pt-0">
            <p className="text-sm font-bold text-foreground">هنوز دیدگاهی نیست</p>
            <p className="mt-0.5 text-xs leading-6 text-muted-foreground sm:text-sm sm:leading-6">
              اولین نفری باشید که تجربهٔ خرید را می‌نویسد.
            </p>
          </div>
        </div>
      ) : (
        <ul className="divide-y divide-steel/[0.07]">
          {data!.map((c) => {
            const dateLabel = formatCommentDate(c.created_at);
            return (
              <li key={c.id} className="py-3.5 first:pt-1 last:pb-1 sm:py-4">
                <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1.5">
                  <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
                    <span className="font-bold text-foreground">{c.author_name}</span>
                    {c.is_verified_buyer ? (
                      <span className="inline-flex items-center gap-0.5 text-[11px] font-bold text-success">
                        <ShieldDone size="small" set="bold" />
                        خریدار
                      </span>
                    ) : null}
                    {dateLabel ? (
                      <time
                        dateTime={c.created_at}
                        className="text-[11px] text-muted-foreground tnum sm:text-xs"
                      >
                        {dateLabel}
                      </time>
                    ) : null}
                  </div>
                  <Stars rating={c.rating} />
                </div>
                <p className="mt-2 text-sm leading-7 text-foreground/85">{c.body}</p>
              </li>
            );
          })}
        </ul>
      )}

      {/* Write form — single interaction surface */}
      <div
        id={formId}
        className="scroll-mt-28 rounded-xl border border-steel/[0.08] bg-secondary/30 px-3.5 py-4 sm:px-5"
      >
        <div className="mb-3.5 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
          <h3 className="text-sm font-bold text-foreground sm:text-base">ثبت دیدگاه</h3>
          <p className="text-[11px] leading-5 text-muted-foreground sm:text-xs sm:leading-5">
            پس از بررسی کوتاه منتشر می‌شود.
          </p>
        </div>

        {!loggedIn ? (
          <div className="flex flex-col gap-2.5 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm leading-6 text-muted-foreground">
              برای نوشتن دیدگاه وارد حساب شوید.
            </p>
            <Link
              href={loginHref}
              className={cn(
                buttonVariants({ variant: "outline", size: "sm" }),
                "shrink-0 self-start sm:self-auto",
              )}
            >
              ورود / ثبت‌نام
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-3.5">
            <div className="grid gap-3.5 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end sm:gap-4">
              <Field label="نام نمایشی" className="min-w-0">
                <input
                  className={cn(fieldInputClass, "h-11")}
                  placeholder="مثلاً علی"
                  value={authorName}
                  onChange={(e) => setAuthorName(e.target.value)}
                  autoComplete="nickname"
                />
              </Field>

              <div className="sm:pb-0.5">
                <span className="mb-1.5 block text-sm font-bold text-foreground">امتیاز</span>
                <div className="inline-flex h-11 items-center rounded-xl bg-input px-2.5">
                  <Stars rating={rating} onSelect={setRating} size="medium" showValue />
                </div>
              </div>
            </div>

            <Field label="متن دیدگاه">
              <textarea
                className={cn(fieldTextareaClass, "min-h-[5.5rem] resize-y py-3")}
                placeholder="تجربهٔ استفاده از این محصول را بنویسید…"
                value={body}
                onChange={(e) => setBody(e.target.value)}
              />
            </Field>

            {formError ? (
              <p className="text-sm text-destructive" role="alert">
                {formError}
              </p>
            ) : null}
            {formSuccess ? (
              <p
                className="rounded-lg bg-success/10 px-3 py-2 text-sm leading-6 text-success"
                role="status"
              >
                {formSuccess}
              </p>
            ) : null}

            <div className="flex justify-end pt-0.5">
              <Button type="submit" disabled={createComment.isPending} className="min-w-[8rem]">
                {createComment.isPending ? "در حال ارسال…" : "ارسال دیدگاه"}
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
