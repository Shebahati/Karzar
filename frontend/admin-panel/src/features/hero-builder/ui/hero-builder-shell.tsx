"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  featuredIndexForSlide,
  HERO_FEATURED_SLOT_COUNT,
  HERO_SLIDE_SLOT_COUNT,
  MOBILE_COMPOSE_PRESETS,
  useHeroBuilderStore,
} from "@/entities/hero";
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

type Phase = "slides" | "dock" | "edit";

const PHASE_TABS: { id: Phase; label: string }[] = [
  { id: "slides", label: "اسلایدها" },
  { id: "dock", label: "داک" },
  { id: "edit", label: "تنظیمات و پیش‌نمایش" },
];

export function HeroBuilderShell() {
  const [phase, setPhase] = useState<Phase>("slides");
  const [publishing, setPublishing] = useState(false);

  const store = useHeroBuilderStore();
  const { data: tree = [] } = useCategories();
  const { project, dirty } = store;
  const config = store.activeConfig();
  const activeSlide = store.activeSlide();
  const activeMobilePreset = resolveSlidePreset(activeSlide, project.mobilePreset);
  const issues = store.validationIssues();

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

  const publish = async () => {
    const blockers = store.validationIssues();
    if (blockers.length) {
      toast.error(blockers[0]!.message);
      return;
    }
    setPublishing(true);
    try {
      const pack = store.toPublishedPack();
      if (pack.slides.length !== HERO_SLIDE_SLOT_COUNT) {
        toast.error(`انتشار فقط با دقیقاً ${HERO_SLIDE_SLOT_COUNT} اسلاید فعال ممکن است`);
        return;
      }
      const result = await publishHeroPack(pack);
      if (result.fileOk) {
        store.markClean();
        const featuredCount = pack.categoryDock.categories.filter(
          (c) => c.featuredOrder != null,
        ).length;
        toast.success(
          `منتشر شد · ${pack.slides.length} اسلاید · ${featuredCount}/${HERO_FEATURED_SLOT_COUNT} داک${result.cms ? ` · CMS: ${result.cms.updated} به‌روز / ${result.cms.created} جدید` : ""}`,
        );
      } else {
        toast.error(result.detail ?? "انتشار فایل ناموفق بود");
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "خطا در انتشار");
    } finally {
      setPublishing(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-7.5rem)] min-h-[640px] flex-col gap-3">
      <header className="rounded-2xl border border-[#E8E8E8] bg-white px-4 py-3 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <nav className="flex rounded-xl bg-[#F5F5F5] p-1" aria-label="مراحل هیرو">
              {PHASE_TABS.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => {
                    if (tab.id === "edit" && activeSlide?.isPlaceholder) {
                      toast.message("اول یک اسلات اسلاید را پر کنید");
                      setPhase("slides");
                      return;
                    }
                    setPhase(tab.id);
                  }}
                  className={cn(
                    "rounded-lg px-3 py-1.5 text-[11px] font-bold transition",
                    phase === tab.id
                      ? "bg-white text-[#1A1A1A] shadow-sm"
                      : "text-[#5E5F5E] hover:text-[#1A1A1A]",
                  )}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
            {dirty ? (
              <span className="rounded-lg bg-amber-500/15 px-2 py-0.5 text-[10px] font-bold text-amber-700">
                ذخیره‌نشده
              </span>
            ) : null}
            {issues.length ? (
              <span className="rounded-lg bg-[#D02327]/10 px-2 py-0.5 text-[10px] font-bold text-[#D02327]">
                {issues.length} مورد برای انتشار
              </span>
            ) : null}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {phase === "edit" ? (
              <>
                <div className="flex items-center gap-2 rounded-xl bg-[#F5F5F5] px-2.5 py-1.5">
                  <span className="text-[11px] font-bold text-[#5E5F5E]">گرید</span>
                  <Switch
                    checked={project.showGrid}
                    onCheckedChange={(showGrid) => store.setGrid({ showGrid })}
                    disabled={project.previewDevice === "mobile"}
                  />
                  <span className="text-[11px] font-bold text-[#5E5F5E]">اسنپ</span>
                  <Switch
                    checked={project.snapToGrid}
                    onCheckedChange={(snapToGrid) => store.setGrid({ snapToGrid })}
                    disabled={project.previewDevice === "mobile"}
                  />
                </div>
                <div className="flex rounded-xl bg-[#F5F5F5] p-1">
                  {(["desktop", "tablet", "mobile"] as const).map((device) => (
                    <button
                      key={device}
                      type="button"
                      onClick={() => store.setPreviewDevice(device)}
                      className={cn(
                        "rounded-lg px-3 py-1.5 text-[11px] font-bold transition",
                        project.previewDevice === device
                          ? "bg-white text-[#1A1A1A] shadow-sm"
                          : "text-[#5E5F5E]",
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
              </>
            ) : null}
            <Button type="button" size="sm" disabled={publishing} onClick={() => void publish()}>
              {publishing ? "در حال انتشار…" : "انتشار روی سایت"}
            </Button>
          </div>
        </div>
      </header>

      {phase === "slides" ? (
        <div className="min-h-0 flex-1 overflow-y-auto">
          <HeroSlidePicker
            onEnter={() => setPhase("edit")}
            onOpenDock={() => setPhase("dock")}
          />
        </div>
      ) : null}

      {phase === "dock" ? (
        <div className="min-h-0 flex-1 overflow-y-auto">
          <HeroDockManager onBack={() => setPhase("slides")} />
        </div>
      ) : null}

      {phase === "edit" ? (
        <>
          {project.previewDevice === "mobile" && activeSlide && !activeSlide.isPlaceholder ? (
            <div className="rounded-2xl border border-[#E8E8E8] bg-white p-3 shadow-sm">
              <div className="mb-2 flex items-baseline justify-between gap-2 px-1">
                <h2 className="text-xs font-black text-[#1A1A1A]">قالب موبایل این اسلاید</h2>
                <span className="text-[10px] text-[#5E5F5E]">
                  فقط متن و دکمه — چیدمان از قالب
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
                          ? "bg-[#D02327] text-white ring-[#D02327]"
                          : "bg-[#F5F5F5] text-[#1A1A1A] ring-[#E8E8E8] hover:bg-[#EFEFEF]",
                      )}
                    >
                      <div className="text-[11px] font-black">{p.label}</div>
                      <div
                        className={cn(
                          "mt-0.5 text-[9px] leading-snug",
                          selected ? "text-white/80" : "text-[#5E5F5E]",
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
              .map((slide, i) => (
                <button
                  key={slide.id}
                  type="button"
                  onClick={() => {
                    if (slide.isPlaceholder) {
                      toast.message("این اسلات خالی است — از تب اسلایدها پر کنید");
                      setPhase("slides");
                      return;
                    }
                    store.selectSlide(slide.id);
                  }}
                  className={cn(
                    "shrink-0 rounded-xl px-3 py-2 text-xs font-bold",
                    project.activeSlideId === slide.id
                      ? "bg-[#D02327] text-white"
                      : "border border-[#E8E8E8] bg-white text-[#1A1A1A]",
                    slide.isPlaceholder && "border-dashed opacity-60",
                    !slide.isActive && !slide.isPlaceholder && "opacity-60",
                  )}
                >
                  {i + 1}. {slide.isPlaceholder ? "خالی" : slide.name}
                  {slide.config.linkedOrbKey ? (
                    <span className="ms-1 text-[9px] opacity-70">· داک</span>
                  ) : null}
                </button>
              ))}
          </div>

          <div className="grid min-h-0 flex-1 gap-3 lg:grid-cols-[minmax(0,1fr)_min(380px,34vw)]">
            <div className="flex min-h-0 flex-col overflow-auto rounded-[1.5rem] bg-[linear-gradient(165deg,#ececec,#f7f7f7)] p-4 shadow-sm ring-1 ring-inset ring-[#E0E0E0]">
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
                    activeOrbIndex={featuredIndexForSlide(
                      activeSlide,
                      project.categoryDock,
                    )}
                    onSelectOrb={(orbKey) => {
                      const linked = project.slides.find(
                        (s) => s.config.linkedOrbKey === orbKey && !s.isPlaceholder,
                      );
                      if (linked) {
                        store.selectSlide(linked.id);
                        return;
                      }
                      toast.message("این پاور به اسلایدی وصل نیست — از تب داک وصل کنید");
                    }}
                    onSelectLayer={store.selectLayer}
                    onMoveLayer={store.moveLayer}
                  />
                </div>
              </div>
              <p className="mt-3 text-center text-[11px] text-[#5E5F5E]">
                پیش‌نمایش: کلیک روی پاور، اسلاید متصل را نشان می‌دهد (در سایت زنده، پاور به صفحهٔ دسته می‌رود)
              </p>
            </div>

            <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[1.5rem] border border-[#E8E8E8] bg-white p-3 shadow-sm">
              <div className="mb-2 shrink-0 px-1 text-xs font-bold text-[#5E5F5E]">
                {project.previewDevice === "mobile"
                  ? "موبایل · متن و دکمه‌ها"
                  : "تنظیمات اسلاید فعال"}
              </div>
              <div className="min-h-0 min-w-0 flex-1 overflow-y-auto overflow-x-hidden overscroll-contain pe-1">
                <HeroSettingsSidebar />
              </div>
            </aside>
          </div>
        </>
      ) : null}
    </div>
  );
}
