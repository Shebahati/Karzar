"use client";

import { useMemo, useState } from "react";
import { Delete, Edit, Image2, Plus } from "react-iconly";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StepUpDialog } from "@/components/step-up-dialog";
import { HeroSlideFormDialog } from "@/features/cms/components/hero-slide-form-dialog";
import {
  useCreateHeroSlide,
  useDeleteHeroSlide,
  useHeroSlides,
  useUpdateHeroSlide,
} from "@/features/cms/queries";
import { ApiError } from "@/lib/api-client";
import type { HeroSlide, HeroSlideCreatePayload } from "@/types/cms";

export default function HeroSlidesPage() {
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<HeroSlide | null>(null);
  const [target, setTarget] = useState<HeroSlide | null>(null);

  const listParams = useMemo(() => ({ limit: 50 }), []);
  const { data, isPending, isError, error, refetch, isFetching } = useHeroSlides(listParams);
  const slides = data?.data ?? [];

  const createSlide = useCreateHeroSlide();
  const updateSlide = useUpdateHeroSlide();
  const deleteSlide = useDeleteHeroSlide();

  const nextSortOrder = slides.length > 0 ? Math.max(...slides.map((s) => s.sort_order)) + 1 : 1;

  function openCreate() {
    setEditing(null);
    setFormOpen(true);
  }

  function openEdit(slide: HeroSlide) {
    setEditing(slide);
    setFormOpen(true);
  }

  async function handleFormSubmit(payload: HeroSlideCreatePayload) {
    try {
      if (editing) {
        await updateSlide.mutateAsync({ id: editing.id, payload });
        toast.success("اسلاید به‌روزرسانی شد");
      } else {
        await createSlide.mutateAsync(payload);
        toast.success("اسلاید ایجاد شد");
      }
      setFormOpen(false);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "ذخیره اسلاید ناموفق بود");
      throw err;
    }
  }

  function handleVerified(stepUpToken: string) {
    if (!target) return;
    const title = target.title;
    deleteSlide.mutate(
      { id: target.id, stepUpToken },
      {
        onSuccess: () => {
          toast.success("اسلاید حذف شد", { description: `«${title}» حذف گردید.` });
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
          <h2 className="text-2xl font-bold text-[#4F4F4F]">اسلایدهای هدر</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {data ? `${data.meta.total_count.toLocaleString("fa-IR")} اسلاید` : "مدیریت بنر اصلی صفحه نخست"}
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus set="bold" size={20} primaryColor="#FFFFFF" />
          افزودن اسلاید
        </Button>
      </div>

      <Card className="border-transparent shadow-sm">
        <CardContent className="p-0">
          {isPending ? (
            <div className="flex flex-col gap-3 p-6">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-20 w-full" />
              ))}
            </div>
          ) : isError ? (
            <div className="flex flex-col items-center gap-3 py-16 text-center">
              <p className="text-sm font-bold text-foreground">
                {error instanceof ApiError ? error.message : "خطا در دریافت اسلایدها"}
              </p>
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                تلاش مجدد
              </Button>
            </div>
          ) : slides.length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-16 text-center">
              <Image2 set="bulk" size={48} primaryColor="#BDBDBD" />
              <p className="text-sm font-bold text-foreground">اسلایدی یافت نشد</p>
            </div>
          ) : (
            <ul className={`flex flex-col gap-1 p-3 ${isFetching ? "opacity-60" : ""}`}>
              {slides.map((slide) => (
                <li
                  key={slide.id}
                  className="flex flex-wrap items-center gap-4 rounded-lg px-4 py-3 transition-colors hover:bg-[#F7F7F7]"
                >
                  <span
                    className="h-14 w-24 shrink-0 rounded-lg bg-cover bg-center shadow-soft"
                    style={{ backgroundImage: `url(${slide.image})`, backgroundColor: slide.accent }}
                  />
                  <div className="flex min-w-0 flex-1 flex-col">
                    <span className="truncate text-sm font-bold text-[#4F4F4F]">{slide.title}</span>
                    {slide.subtitle && (
                      <span className="truncate text-xs text-muted-foreground">{slide.subtitle}</span>
                    )}
                  </div>
                  <span
                    className="h-6 w-6 shrink-0 rounded-md shadow-soft"
                    style={{ backgroundColor: slide.accent }}
                    title={slide.accent}
                  />
                  <span className="text-xs text-muted-foreground tnum">
                    ترتیب {slide.sort_order.toLocaleString("fa-IR")}
                  </span>
                  <span>
                    {slide.is_active ? (
                      <Badge variant="success">فعال</Badge>
                    ) : (
                      <Badge variant="outline">غیرفعال</Badge>
                    )}
                  </span>
                  <div className="flex justify-end gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label="ویرایش اسلاید"
                      onClick={() => openEdit(slide)}
                    >
                      <Edit set="light" size={20} primaryColor="currentColor" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label="حذف اسلاید"
                      className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                      onClick={() => setTarget(slide)}
                    >
                      <Delete set="light" size={20} primaryColor="currentColor" />
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <HeroSlideFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        mode={editing ? "edit" : "create"}
        slide={editing}
        nextSortOrder={nextSortOrder}
        onSubmit={handleFormSubmit}
        pending={createSlide.isPending || updateSlide.isPending}
      />

      <StepUpDialog
        open={target !== null}
        onOpenChange={(open) => (!open ? setTarget(null) : undefined)}
        onVerified={handleVerified}
        actionPending={deleteSlide.isPending}
        title="حذف اسلاید"
        description={target ? `برای حذف «${target.title}» کد امنیتی مدیر را وارد کنید.` : undefined}
      />
    </div>
  );
}
