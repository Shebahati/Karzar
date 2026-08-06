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
}: {
  rating: number;
  onSelect?: (value: number) => void;
  size?: "small" | "medium";
}) {
  return (
    <div className="flex items-center gap-0.5" role={onSelect ? "radiogroup" : "img"} aria-label={`${rating} از ۵`}>
      {Array.from({ length: 5 }).map((_, i) => {
        const active = i < rating;
        const common = cn(
          "transition-colors",
          active ? "text-warning" : "text-muted-foreground/35",
          onSelect && "rounded-md p-0.5 hover-fine:text-warning",
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

  return (
    <div className="space-y-8">
      {avgRating != null ? (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <div className="flex items-baseline gap-1.5">
            <span className="text-2xl font-bold tracking-tight text-foreground tnum">
              {avgRating.toFixed(1)}
            </span>
            <span className="text-sm text-muted-foreground">از ۵</span>
          </div>
          <Stars rating={Math.round(avgRating)} size="medium" />
          <span className="text-sm text-muted-foreground tnum">
            {data!.length.toLocaleString("fa-IR")} دیدگاه
          </span>
        </div>
      ) : null}

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 2 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full rounded-2xl" />
          ))}
        </div>
      ) : !hasReviews ? (
        <div
          className="flex flex-col items-center rounded-2xl border border-dashed border-steel/20 bg-secondary/30 px-5 py-10 text-center sm:px-8"
          role="status"
        >
          <span
            className="mb-4 grid h-12 w-12 place-items-center rounded-2xl bg-white/70 text-muted-foreground/70"
            aria-hidden
          >
            <Chat size="medium" set="light" />
          </span>
          <p className="text-[15px] font-bold text-foreground">هنوز دیدگاهی نیست</p>
          <p className="mt-1.5 max-w-sm text-sm leading-7 text-muted-foreground">
            اولین نفری باشید که تجربهٔ خود را می‌نویسد.
          </p>
          {!loggedIn ? (
            <Link
              href={loginHref}
              className={cn(buttonVariants({ variant: "soft", size: "sm" }), "mt-5")}
            >
              ورود برای ثبت دیدگاه
            </Link>
          ) : (
            <a
              href={`#${formId}`}
              className={cn(buttonVariants({ variant: "soft", size: "sm" }), "mt-5")}
            >
              نوشتن دیدگاه
            </a>
          )}
        </div>
      ) : (
        <ul className="divide-y divide-steel/[0.08] rounded-2xl bg-secondary/25 px-4 sm:px-5">
          {data!.map((c) => {
            const dateLabel = formatCommentDate(c.created_at);
            return (
              <li key={c.id} className="py-5 first:pt-4 last:pb-4 sm:py-6">
                <div className="flex flex-wrap items-start justify-between gap-x-3 gap-y-2">
                  <div className="min-w-0 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-bold text-foreground">{c.author_name}</span>
                      {c.is_verified_buyer ? (
                        <span className="inline-flex items-center gap-1 rounded-md bg-success/10 px-2 py-0.5 text-[11px] font-bold text-success">
                          <ShieldDone size="small" set="bold" />
                          خریدار
                        </span>
                      ) : null}
                    </div>
                    {dateLabel ? (
                      <time
                        dateTime={c.created_at}
                        className="block text-xs text-muted-foreground tnum"
                      >
                        {dateLabel}
                      </time>
                    ) : null}
                  </div>
                  <Stars rating={c.rating} />
                </div>
                <p className="mt-3 text-sm leading-7 text-foreground/85">{c.body}</p>
              </li>
            );
          })}
        </ul>
      )}

      <div
        id={formId}
        className="scroll-mt-28 rounded-2xl bg-secondary/40 px-4 py-5 sm:px-6 sm:py-6"
      >
        <div className="mb-4">
          <h3 className="text-base font-bold text-foreground">نظر شما</h3>
          <p className="mt-1 text-xs leading-6 text-muted-foreground">
            پس از بررسی کوتاه نمایش داده می‌شود.
          </p>
        </div>

        {!loggedIn ? (
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm leading-7 text-muted-foreground">
              برای نوشتن دیدگاه وارد حساب شوید.
            </p>
            <Link
              href={loginHref}
              className={cn(buttonVariants({ variant: "outline", size: "sm" }), "shrink-0 self-start sm:self-auto")}
            >
              ورود / ثبت‌نام
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <Field label="نام نمایشی">
              <input
                className={fieldInputClass}
                placeholder="مثلاً علی"
                value={authorName}
                onChange={(e) => setAuthorName(e.target.value)}
                autoComplete="nickname"
              />
            </Field>

            <div>
              <span className="mb-1.5 block text-sm font-bold text-foreground">امتیاز</span>
              <Stars rating={rating} onSelect={setRating} size="medium" />
            </div>

            <Field label="متن دیدگاه">
              <textarea
                className={cn(fieldTextareaClass, "min-h-[7.5rem] resize-y")}
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
              <p className="rounded-xl bg-success/10 px-3 py-2.5 text-sm leading-6 text-success" role="status">
                {formSuccess}
              </p>
            ) : null}

            <Button type="submit" disabled={createComment.isPending} className="min-w-[8.5rem]">
              {createComment.isPending ? "در حال ارسال…" : "ارسال دیدگاه"}
            </Button>
          </form>
        )}
      </div>
    </div>
  );
}
