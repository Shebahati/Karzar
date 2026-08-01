"use client";

import { useHeroBuilderStore, createDefaultProject } from "@/entities/hero";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

export function HeroSlidePicker({
  onEnter,
  onOpenDock,
}: {
  onEnter: () => void;
  onOpenDock?: () => void;
}) {
  const {
    project,
    selectSlide,
    addSlide,
    duplicateSlide,
    removeSlide,
    renameSlide,
    setSlideActive,
    reorderSlide,
    importProject,
  } = useHeroBuilderStore();

  const slides = [...project.slides].sort((a, b) => a.sortOrder - b.sortOrder);

  return (
    <div className="flex h-[calc(100vh-7.5rem)] min-h-[560px] flex-col gap-5">
      <header className="flex flex-wrap items-end justify-between gap-3 rounded-2xl bg-card px-5 py-4 shadow-soft">
        <div>
          <h1 className="text-xl font-black text-ink">اسلایدهای هیرو</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            شش اسلاید پاور کارزار آماده است — ویرایش کنید یا پکیج پیش‌فرض را دوباره بارگذاری کنید.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              importProject(createDefaultProject());
              toast.success("پکیج ۶ اسلایدی کارزار بارگذاری شد");
            }}
          >
            بارگذاری پکیج ۶ اسلایدی
          </Button>
          {onOpenDock ? (
            <Button type="button" variant="outline" onClick={onOpenDock}>
              مدیریت داک دسته‌ها
            </Button>
          ) : null}
        </div>
      </header>

      <div className="grid flex-1 gap-4 overflow-y-auto pb-4 sm:grid-cols-2 xl:grid-cols-3">
        {slides.map((slide, index) => {
          const bg =
            slide.config.background.mode === "image"
              ? slide.config.background.imageUrl
              : undefined;
          const selected = project.activeSlideId === slide.id;
          return (
            <article
              key={slide.id}
              className={cn(
                "group flex flex-col overflow-hidden rounded-2xl bg-card shadow-soft ring-1 ring-inset transition",
                selected ? "ring-primary" : "ring-border/70 hover:ring-border",
              )}
            >
              <button
                type="button"
                className="relative aspect-[16/9] w-full overflow-hidden bg-[#111] text-start"
                onClick={() => {
                  selectSlide(slide.id);
                  onEnter();
                }}
              >
                {bg ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={bg}
                    alt=""
                    className="h-full w-full object-cover"
                    style={{ objectPosition: slide.config.background.focal || "center" }}
                  />
                ) : (
                  <div
                    className="h-full w-full"
                    style={{ background: slide.config.background.color }}
                  />
                )}
                <div className="absolute inset-0 bg-gradient-to-t from-black/75 via-black/20 to-transparent" />
                <div className="absolute inset-x-0 bottom-0 p-3">
                  <div className="text-sm font-bold text-white drop-shadow">
                    {slide.config.typography.title || slide.name}
                  </div>
                  <div className="mt-0.5 line-clamp-1 text-[11px] text-white/80">
                    {slide.config.typography.subtitle}
                  </div>
                </div>
                {!slide.isActive ? (
                  <span className="absolute start-3 top-3 rounded-lg bg-black/55 px-2 py-1 text-[10px] font-bold text-white">
                    غیرفعال
                  </span>
                ) : null}
              </button>

              <div className="flex flex-col gap-2 p-3">
                <input
                  className="h-9 rounded-xl bg-muted px-3 text-sm font-bold outline-none ring-1 ring-inset ring-transparent focus:ring-primary/30"
                  value={slide.name}
                  onChange={(e) => renameSlide(slide.id, e.target.value)}
                />
                <div className="flex flex-wrap gap-1.5">
                  <Button
                    type="button"
                    size="sm"
                    className="flex-1"
                    onClick={() => {
                      selectSlide(slide.id);
                      onEnter();
                    }}
                  >
                    ویرایش
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => duplicateSlide(slide.id)}
                  >
                    کپی
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    disabled={slides.length <= 1}
                    onClick={() => removeSlide(slide.id)}
                  >
                    حذف
                  </Button>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <button
                    type="button"
                    className={cn(
                      "rounded-lg px-2 py-1 text-[11px] font-bold",
                      slide.isActive ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground",
                    )}
                    onClick={() => setSlideActive(slide.id, !slide.isActive)}
                  >
                    {slide.isActive ? "فعال در سایت" : "مخفی از سایت"}
                  </button>
                  <div className="flex gap-1">
                    <button
                      type="button"
                      className="rounded-lg bg-muted px-2 py-1 text-[11px] font-bold disabled:opacity-40"
                      disabled={index === 0}
                      onClick={() => reorderSlide(slide.id, -1)}
                    >
                      ↑
                    </button>
                    <button
                      type="button"
                      className="rounded-lg bg-muted px-2 py-1 text-[11px] font-bold disabled:opacity-40"
                      disabled={index === slides.length - 1}
                      onClick={() => reorderSlide(slide.id, 1)}
                    >
                      ↓
                    </button>
                  </div>
                </div>
              </div>
            </article>
          );
        })}

        <button
          type="button"
          onClick={() => {
            addSlide();
            onEnter();
          }}
          className="flex min-h-[220px] flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-border bg-muted/30 text-muted-foreground transition hover:border-primary/40 hover:bg-primary/5 hover:text-primary"
        >
          <span className="text-3xl font-black">+</span>
          <span className="text-sm font-bold">اسلاید جدید</span>
        </button>
      </div>
    </div>
  );
}
