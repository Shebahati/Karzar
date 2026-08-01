"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { MOBILE_COMPOSE_PRESETS, useHeroBuilderStore } from "@/entities/hero";
import type { MobileComposePreset } from "@/entities/hero";
import { useCategories } from "@/features/catalog/queries";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";
import { publishHeroPack } from "../lib/publish-hero";
import { HeroDockManager } from "./hero-dock-manager";
import { HeroPreview } from "./hero-preview";
import { HeroSettingsSidebar } from "./hero-settings-sidebar";
import { HeroSlidePicker } from "./hero-slide-picker";

function resolveSlidePreset(
  slide: { mobilePreset?: MobileComposePreset } | undefined,
  projectPreset: MobileComposePreset | undefined,
): MobileComposePreset {
  return slide?.mobilePreset ?? projectPreset ?? "balanced";
}

export function HeroBuilderShell() {
  const [phase, setPhase] = useState<"select" | "dock" | "edit">("select");
  const [publishing, setPublishing] = useState(false);

  const store = useHeroBuilderStore();
  const { data: tree = [] } = useCategories();
  const { project, dirty } = store;
  const config = store.activeConfig();
  const activeSlide = store.activeSlide();
  const activeMobilePreset = resolveSlidePreset(activeSlide, project.mobilePreset);

  useEffect(() => {
    const l1 = tree.filter((r) => r.parent_id == null);
    if (!l1.length) return;
    store.syncCategoryDockFromRoots(l1, { appendNew: false });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tree]);

  const frameWidth =
    project.previewDevice === "desktop"
      ? "100%"
      : project.previewDevice === "tablet"
        ? "min(820px, 100%)"
        : "min(390px, 100%)";

  const frameAspect =
    project.previewDevice === "mobile"
      ? "9 / 16"
      : project.previewDevice === "tablet"
        ? "3 / 4"
        : "16 / 10";

  if (phase === "select") {
    return (
      <HeroSlidePicker
        onEnter={() => setPhase("edit")}
        onOpenDock={() => setPhase("dock")}
      />
    );
  }

  if (phase === "dock") {
    return <HeroDockManager onBack={() => setPhase("select")} />;
  }

  return (
    <div className="flex h-[calc(100vh-7.5rem)] min-h-[640px] flex-col gap-3">
      <header className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-card px-4 py-3 shadow-soft">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Button type="button" variant="ghost" size="sm" onClick={() => setPhase("select")}>
              ← اسلایدها
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={() => setPhase("dock")}>
              داک دسته‌ها
            </Button>
            <h1 className="truncate text-lg font-black text-ink">
              {activeSlide?.name ?? "طراحی هیرو"}
            </h1>
            {dirty ? (
              <span className="rounded-lg bg-amber-500/15 px-2 py-0.5 text-[10px] font-bold text-amber-700">
                ذخیره‌نشده
              </span>
            ) : null}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-2 rounded-xl bg-muted px-2.5 py-1.5 shadow-soft">
            <span className="text-[11px] font-bold text-muted-foreground">گرید</span>
            <Switch
              checked={project.showGrid}
              onCheckedChange={(showGrid) => store.setGrid({ showGrid })}
              disabled={project.previewDevice === "mobile"}
            />
            <span className="text-[11px] font-bold text-muted-foreground">اسنپ</span>
            <Switch
              checked={project.snapToGrid}
              onCheckedChange={(snapToGrid) => store.setGrid({ snapToGrid })}
              disabled={project.previewDevice === "mobile"}
            />
          </div>

          <div className="flex rounded-xl bg-muted p-1 shadow-soft">
            {(["desktop", "tablet", "mobile"] as const).map((device) => (
              <button
                key={device}
                type="button"
                onClick={() => store.setPreviewDevice(device)}
                className={cn(
                  "rounded-lg px-3 py-1.5 text-[11px] font-bold transition",
                  project.previewDevice === device
                    ? "bg-card text-ink shadow-soft"
                    : "text-muted-foreground",
                )}
              >
                {device === "desktop" ? "دسکتاپ" : device === "tablet" ? "تبلت" : "موبایل"}
              </button>
            ))}
          </div>

          <Button type="button" variant="ghost" size="sm" onClick={store.undo}>
            بازگشت
          </Button>
          <Button type="button" variant="ghost" size="sm" onClick={store.redo}>
            جلو
          </Button>
          <Button
            type="button"
            size="sm"
            disabled={publishing}
            onClick={async () => {
              setPublishing(true);
              try {
                const pack = store.toPublishedPack();
                if (!pack.slides.length) {
                  toast.error("حداقل یک اسلاید فعال لازم است");
                  return;
                }
                const result = await publishHeroPack(pack);
                if (result.fileOk) {
                  store.markClean();
                  const featuredCount = pack.categoryDock.categories.filter(
                    (c) => c.featuredOrder != null,
                  ).length;
                  toast.success(
                    `منتشر شد · ${featuredCount}/۶ داک هیرو${result.cms ? ` · CMS: ${result.cms.updated} به‌روز / ${result.cms.created} جدید` : ""}`,
                  );
                } else {
                  toast.error(result.detail ?? "انتشار فایل ناموفق بود");
                }
              } catch (err) {
                toast.error(err instanceof Error ? err.message : "خطا در انتشار");
              } finally {
                setPublishing(false);
              }
            }}
          >
            {publishing ? "در حال انتشار…" : "انتشار روی سایت"}
          </Button>
        </div>
      </header>

      {project.previewDevice === "mobile" && activeSlide ? (
        <div className="rounded-2xl bg-card p-3 shadow-soft ring-1 ring-inset ring-border/60">
          <div className="mb-2 flex items-baseline justify-between gap-2 px-1">
            <h2 className="text-xs font-black text-ink">قالب موبایل این اسلاید</h2>
            <span className="text-[10px] text-muted-foreground">
              فقط متن و دکمه ویرایش می‌شود — چیدمان از قالب
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {MOBILE_COMPOSE_PRESETS.map((p) => {
              const selected = activeMobilePreset === p.id;
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => store.setSlideMobilePreset(activeSlide.id, p.id)}
                  className={cn(
                    "rounded-xl px-3 py-2.5 text-start transition ring-1 ring-inset",
                    selected
                      ? "bg-primary text-primary-foreground ring-primary shadow-soft"
                      : "bg-muted/70 text-ink ring-border/70 hover:bg-muted",
                  )}
                >
                  <div className="text-[11px] font-black">{p.label}</div>
                  <div
                    className={cn(
                      "mt-0.5 text-[9px] leading-snug",
                      selected ? "text-white/80" : "text-muted-foreground",
                    )}
                  >
                    {p.hint}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      ) : null}

      <div className="flex gap-2 overflow-x-auto pb-1">
        {[...project.slides]
          .sort((a, b) => a.sortOrder - b.sortOrder)
          .map((slide) => (
            <button
              key={slide.id}
              type="button"
              onClick={() => store.selectSlide(slide.id)}
              className={cn(
                "shrink-0 rounded-xl px-3 py-2 text-xs font-bold shadow-soft",
                project.activeSlideId === slide.id
                  ? "bg-primary text-primary-foreground"
                  : "bg-card text-ink ring-1 ring-inset ring-border/70",
                !slide.isActive && "opacity-60",
              )}
            >
              {slide.name}
              {slide.config.linkedOrbKey ? (
                <span className="ms-1 text-[9px] opacity-70">· دسته</span>
              ) : null}
            </button>
          ))}
      </div>

      <div className="grid min-h-0 flex-1 gap-3 lg:grid-cols-[minmax(0,1fr)_min(380px,34vw)]">
        <div className="flex min-h-0 flex-col overflow-auto rounded-[1.5rem] bg-[linear-gradient(165deg,#ececec,#f7f7f7)] p-4 shadow-soft ring-1 ring-inset ring-border/60">
          <div
            className="mx-auto my-auto w-full transition-all duration-300"
            style={{ width: frameWidth, maxWidth: "100%" }}
          >
            <div style={{ aspectRatio: frameAspect }} className="w-full overflow-hidden rounded-2xl">
              <HeroPreview
                className="!h-full !min-h-0 rounded-2xl"
                config={config}
                selectedLayerId={store.selectedLayerId}
                showGrid={project.showGrid && project.previewDevice !== "mobile"}
                gridSize={project.gridSize}
                lockDrag={project.previewDevice === "mobile"}
                mobilePreset={
                  project.previewDevice === "mobile" ? activeMobilePreset : null
                }
                featuredOrbs={project.categoryDock?.categories
                  ?.filter((c) => c.featuredOrder != null)
                  .sort((a, b) => (a.featuredOrder ?? 0) - (b.featuredOrder ?? 0))
                  .map((c) => ({ key: c.key, name: c.name, icon: c.icon }))}
                activeOrbIndex={Math.max(
                  0,
                  [...project.slides]
                    .sort((a, b) => a.sortOrder - b.sortOrder)
                    .findIndex((s) => s.id === project.activeSlideId),
                )}
                onSelectLayer={store.selectLayer}
                onMoveLayer={store.moveLayer}
              />
            </div>
          </div>
          <p className="mt-3 text-center text-[11px] text-muted-foreground">
            پیش‌نمایش با نسبت واقعی دستگاه · موبایل فقط از قالب‌های امن
          </p>
        </div>

        <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[1.5rem] bg-background p-3 shadow-soft ring-1 ring-inset ring-border/70">
          <div className="mb-2 shrink-0 px-1 text-xs font-bold text-muted-foreground">
            {project.previewDevice === "mobile"
              ? "موبایل · متن و دکمه‌ها"
              : "کنترل پنل اسلاید"}
          </div>
          <div className="min-h-0 min-w-0 flex-1 overflow-y-auto overflow-x-hidden overscroll-contain pe-1">
            <HeroSettingsSidebar />
          </div>
        </aside>
      </div>
    </div>
  );
}
