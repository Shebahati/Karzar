"use client";

import { useMemo, useState } from "react";
import { Delete, Document, Edit, Plus, Search } from "react-iconly";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { StepUpDialog } from "@/components/step-up-dialog";
import { ArticleFormDialog } from "@/features/cms/components/article-form-dialog";
import { useArticles, useCreateArticle, useDeleteArticle, useUpdateArticle } from "@/features/cms/queries";
import { ApiError } from "@/lib/api-client";
import type { Article, ArticleCreatePayload } from "@/types/cms";

export default function ArticlesPage() {
  const [search, setSearch] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Article | null>(null);
  const [target, setTarget] = useState<Article | null>(null);

  const listParams = useMemo(() => ({ limit: 50, search: search.trim() || undefined }), [search]);
  const { data, isPending, isError, error, refetch, isFetching } = useArticles(listParams);
  const articles = data?.data ?? [];

  const createArticle = useCreateArticle();
  const updateArticle = useUpdateArticle();
  const deleteArticle = useDeleteArticle();

  function openCreate() {
    setEditing(null);
    setFormOpen(true);
  }

  function openEdit(article: Article) {
    setEditing(article);
    setFormOpen(true);
  }

  async function handleFormSubmit(payload: ArticleCreatePayload) {
    try {
      if (editing) {
        await updateArticle.mutateAsync({ id: editing.id, payload });
        toast.success("مقاله به‌روزرسانی شد");
      } else {
        await createArticle.mutateAsync(payload);
        toast.success("مقاله ایجاد شد");
      }
      setFormOpen(false);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "ذخیره مقاله ناموفق بود");
      throw err;
    }
  }

  function handleVerified(stepUpToken: string) {
    if (!target) return;
    const title = target.title;
    deleteArticle.mutate(
      { id: target.id, stepUpToken },
      {
        onSuccess: () => {
          toast.success("مقاله حذف شد", { description: `«${title}» حذف گردید.` });
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
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-[#4F4F4F]">مقالات</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {data ? `${data.meta.total_count.toLocaleString("fa-IR")} مقاله` : "مدیریت محتوای وبلاگ فروشگاه"}
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus set="bold" size={20} primaryColor="#FFFFFF" />
          افزودن مقاله
        </Button>
      </div>

      <div className="rounded-xl bg-white p-4 shadow-sm">
        <div className="relative max-w-md">
          <span className="pointer-events-none absolute inset-y-0 start-3 flex items-center text-muted-foreground">
            <Search set="light" size={18} />
          </span>
          <Input
            placeholder="جستجو عنوان یا اسلاگ..."
            className="ps-10"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      <Card className="border-transparent shadow-sm">
        <CardContent className="p-0">
          {isPending ? (
            <div className="flex flex-col gap-3 p-6">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : isError ? (
            <div className="flex flex-col items-center gap-3 py-16 text-center">
              <p className="text-sm font-bold text-foreground">
                {error instanceof ApiError ? error.message : "خطا در دریافت مقالات"}
              </p>
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                تلاش مجدد
              </Button>
            </div>
          ) : articles.length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-16 text-center">
              <Document set="bulk" size={48} primaryColor="#BDBDBD" />
              <p className="text-sm font-bold text-foreground">مقاله‌ای یافت نشد</p>
            </div>
          ) : (
            <div className="flex flex-col p-3">
              <div className="hidden px-4 py-2 text-xs font-bold text-muted-foreground md:grid md:grid-cols-[1fr_120px_140px_100px_96px] md:gap-4">
                <span>عنوان</span>
                <span>نویسنده</span>
                <span>تاریخ انتشار</span>
                <span>وضعیت</span>
                <span />
              </div>
              <ul className={`flex flex-col gap-1 ${isFetching ? "opacity-60" : ""}`}>
                {articles.map((article) => (
                  <li
                    key={article.id}
                    className="grid grid-cols-1 items-center gap-2 rounded-lg px-4 py-3 transition-colors hover:bg-[#F7F7F7] md:grid-cols-[1fr_120px_140px_100px_96px] md:gap-4"
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-accent text-primary">
                        <Document set="bulk" size={20} primaryColor="#C22026" />
                      </div>
                      <div className="flex min-w-0 flex-col">
                        <span className="truncate text-sm font-bold text-[#4F4F4F]">{article.title}</span>
                        <span dir="ltr" className="text-start text-xs text-muted-foreground">
                          /{article.slug}
                        </span>
                      </div>
                    </div>
                    <span className="truncate text-sm text-muted-foreground">{article.author}</span>
                    <span className="text-xs text-muted-foreground tnum">
                      {new Date(article.published_at).toLocaleDateString("fa-IR")}
                    </span>
                    <span>
                      {article.is_published ? (
                        <Badge variant="success">منتشر شده</Badge>
                      ) : (
                        <Badge variant="outline">پیش‌نویس</Badge>
                      )}
                    </span>
                    <div className="flex justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label="ویرایش مقاله"
                        onClick={() => openEdit(article)}
                      >
                        <Edit set="light" size={20} primaryColor="currentColor" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label="حذف مقاله"
                        className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                        onClick={() => setTarget(article)}
                      >
                        <Delete set="light" size={20} primaryColor="currentColor" />
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>

      <ArticleFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        mode={editing ? "edit" : "create"}
        article={editing}
        onSubmit={handleFormSubmit}
        pending={createArticle.isPending || updateArticle.isPending}
      />

      <StepUpDialog
        open={target !== null}
        onOpenChange={(open) => (!open ? setTarget(null) : undefined)}
        onVerified={handleVerified}
        actionPending={deleteArticle.isPending}
        title="حذف مقاله"
        description={target ? `برای حذف «${target.title}» کد امنیتی مدیر را وارد کنید.` : undefined}
      />
    </div>
  );
}
