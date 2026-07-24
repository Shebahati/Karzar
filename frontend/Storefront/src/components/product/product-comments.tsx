"use client";

import { useEffect, useState } from "react";
import { Star, ShieldDone } from "react-iconly";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { useComments, catalogKeys } from "@/features/catalog/queries";
import { catalogService } from "@/services/catalog";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { ApiError, isLoggedIn as checkLoggedIn } from "@/lib/api-client";

function Stars({
  rating,
  onSelect,
}: {
  rating: number;
  onSelect?: (value: number) => void;
}) {
  return (
    <div className="flex items-center gap-0.5">
      {Array.from({ length: 5 }).map((_, i) => (
        <button
          key={i}
          type="button"
          disabled={!onSelect}
          className={i < rating ? "text-warning" : "text-muted-foreground/40"}
          onClick={() => onSelect?.(i + 1)}
          aria-label={`${i + 1} ستاره`}
        >
          <Star size="small" set={i < rating ? "bold" : "light"} />
        </button>
      ))}
    </div>
  );
}

export function ProductComments({ productId }: { productId: number }) {
  const { data, isLoading } = useComments(productId);
  const queryClient = useQueryClient();
  const [loggedIn, setLoggedIn] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [formSuccess, setFormSuccess] = useState<string | null>(null);

  const [authorName, setAuthorName] = useState("");
  const [rating, setRating] = useState(5);
  const [body, setBody] = useState("");

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

  return (
    <div className="space-y-6">
      {avgRating != null && (
        <div className="flex items-center gap-2 text-sm text-warning">
          <Star size="small" set="bold" />
          <span className="font-bold tnum">{avgRating.toFixed(1)}</span>
          <span className="text-muted-foreground tnum">از {data!.length} دیدگاه</span>
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        className="space-y-3 rounded-2xl border border-border/60 bg-card p-5 shadow-soft"
      >
        <h3 className="text-sm font-bold text-foreground">ثبت دیدگاه</h3>
        <p className="text-xs leading-6 text-muted-foreground">
          دیدگاه‌ها پس از بررسی نمایش داده می‌شوند و ممکن است بلافاصله در این صفحه دیده نشوند.
        </p>
        {!loggedIn ? (
          <p className="text-sm text-muted-foreground">
            برای ثبت دیدگاه ابتدا وارد حساب کاربری شوید.
          </p>
        ) : (
          <>
            <input
              className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm"
              placeholder="نام نمایشی"
              value={authorName}
              onChange={(e) => setAuthorName(e.target.value)}
            />
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">امتیاز:</span>
              <Stars rating={rating} onSelect={setRating} />
            </div>
            <textarea
              className="min-h-24 w-full rounded-xl border border-border bg-background px-3 py-2 text-base"
              placeholder="تجربه خود را بنویسید..."
              value={body}
              onChange={(e) => setBody(e.target.value)}
            />
            {formError && <p className="text-sm text-destructive">{formError}</p>}
            {formSuccess && <p className="text-sm text-success">{formSuccess}</p>}
            <Button type="submit" disabled={createComment.isPending}>
              {createComment.isPending ? "در حال ارسال..." : "ارسال دیدگاه"}
            </Button>
          </>
        )}
      </form>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 2 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-2xl" />
          ))}
        </div>
      ) : !data?.length ? (
        <div className="rounded-2xl bg-card p-8 text-center text-sm text-muted-foreground shadow-soft">
          هنوز دیدگاهی برای این محصول ثبت نشده است. اولین نفر باشید!
        </div>
      ) : (
        <div className="space-y-4">
          {data.map((c) => (
            <div key={c.id} className="rounded-2xl bg-card p-5 shadow-soft">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-foreground">{c.author_name}</span>
                  {c.is_verified_buyer && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-success/10 px-2 py-0.5 text-xs font-bold text-success">
                      <ShieldDone size="small" set="bold" />
                      خریدار
                    </span>
                  )}
                </div>
                <Stars rating={c.rating} />
              </div>
              <p className="mt-3 text-sm leading-7 text-foreground/90">{c.body}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
