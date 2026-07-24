"use client";

import { useMemo, useState } from "react";
import { Delete, Message, Star } from "react-iconly";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { StepUpDialog } from "@/components/step-up-dialog";
import { useDeleteProductComment, useProductComments } from "@/features/cms/queries";
import { ApiError } from "@/lib/api-client";
import { toPersianDigits } from "@/lib/utils";
import type { ProductComment } from "@/types/cms";

const PAGE_SIZE = 20;

function RatingStars({ rating }: { rating: number }) {
  return (
    <span className="flex items-center gap-0.5" title={`${rating} از ۵`}>
      {Array.from({ length: 5 }).map((_, i) => (
        <Star
          key={i}
          set={i < rating ? "bold" : "light"}
          size={14}
          primaryColor={i < rating ? "#F5A623" : "#D0D0D0"}
        />
      ))}
    </span>
  );
}

export default function ProductCommentsPage() {
  const [productIdFilter, setProductIdFilter] = useState("");
  const [skip, setSkip] = useState(0);
  const [target, setTarget] = useState<ProductComment | null>(null);

  const listParams = useMemo(
    () => ({
      skip,
      limit: PAGE_SIZE,
      product_id: productIdFilter.trim() ? Number(productIdFilter.trim()) : undefined,
    }),
    [skip, productIdFilter],
  );

  const { data, isPending, isError, error, refetch, isFetching } = useProductComments(listParams);
  const comments = data?.data ?? [];
  const deleteComment = useDeleteProductComment();

  function handleVerified(stepUpToken: string) {
    if (!target) return;
    deleteComment.mutate(
      { id: target.id, stepUpToken },
      {
        onSuccess: () => {
          toast.success("نظر حذف شد");
          setTarget(null);
        },
        onError: (err) => {
          const message = err instanceof ApiError ? err.message : "حذف ناموفق بود.";
          toast.error("حذف ناموفق بود", { description: message });
          setTarget(null);
        },
      },
    );
  }

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <div>
        <h2 className="text-2xl font-bold text-[#4F4F4F]">نظرات محصولات</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          {data ? `${data.meta.total_count.toLocaleString("fa-IR")} نظر` : "مدیریت نظرات ثبت‌شده روی محصولات"}
        </p>
      </div>

      <div className="rounded-xl bg-white p-4 shadow-sm">
        <div className="max-w-xs">
          <Input
            placeholder="فیلتر بر اساس شناسه محصول..."
            dir="ltr"
            className="text-start tnum"
            value={productIdFilter}
            onChange={(e) => {
              setProductIdFilter(e.target.value.replace(/[^\d]/g, ""));
              setSkip(0);
            }}
          />
        </div>
      </div>

      <Card className="border-transparent shadow-sm">
        <CardContent className="p-0">
          {isPending ? (
            <div className="flex flex-col gap-3 p-6">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-20 w-full" />
              ))}
            </div>
          ) : isError ? (
            <div className="flex flex-col items-center gap-3 py-16 text-center">
              <p className="text-sm font-bold text-foreground">
                {error instanceof ApiError ? error.message : "خطا در دریافت نظرات"}
              </p>
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                تلاش مجدد
              </Button>
            </div>
          ) : comments.length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-16 text-center">
              <Message set="bulk" size={48} primaryColor="#BDBDBD" />
              <p className="text-sm font-bold text-foreground">نظری یافت نشد</p>
            </div>
          ) : (
            <ul className={`divide-y divide-gray-100 ${isFetching ? "opacity-60" : ""}`}>
              {comments.map((comment) => (
                <li key={comment.id} className="flex flex-wrap items-start justify-between gap-4 px-4 py-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-[#4F4F4F]">{comment.author_name}</span>
                      {comment.is_verified_buyer && (
                        <Badge variant="success" className="text-[10px]">
                          خریدار تأیید شده
                        </Badge>
                      )}
                      <Badge variant="outline" className="text-[10px] tnum">
                        محصول #{toPersianDigits(comment.product_id)}
                      </Badge>
                    </div>
                    <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{comment.body}</p>
                    <div className="mt-2 flex items-center gap-3">
                      <RatingStars rating={comment.rating} />
                      <span className="text-xs text-muted-foreground">
                        {new Date(comment.created_at).toLocaleDateString("fa-IR")}
                      </span>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label="حذف نظر"
                    className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                    onClick={() => setTarget(comment)}
                  >
                    <Delete set="light" size={20} primaryColor="currentColor" />
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {data && data.meta.total_count > 0 && (
        <div className="flex items-center justify-between gap-3">
          <span className="text-xs text-muted-foreground">
            نمایش {toPersianDigits(skip + 1)}–{toPersianDigits(Math.min(skip + PAGE_SIZE, data.meta.total_count))} از{" "}
            {toPersianDigits(data.meta.total_count)}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={!data.meta.has_prev}
              onClick={() => setSkip((s) => Math.max(0, s - PAGE_SIZE))}
            >
              قبلی
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={!data.meta.has_next}
              onClick={() => setSkip((s) => s + PAGE_SIZE)}
            >
              بعدی
            </Button>
          </div>
        </div>
      )}

      <StepUpDialog
        open={target !== null}
        onOpenChange={(open) => (!open ? setTarget(null) : undefined)}
        onVerified={handleVerified}
        actionPending={deleteComment.isPending}
        title="حذف نظر"
        description={target ? `برای حذف نظر «${target.author_name}» کد امنیتی مدیر را وارد کنید.` : undefined}
      />
    </div>
  );
}
