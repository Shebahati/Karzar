"use client";

/**
 * Lightweight zustand-compatible store + persist shim.
 * Charter forbids adding zustand to admin-panel package.json / lockfile;
 * Storefront already has zustand — admin hero builder must not bump deps.
 */
import { useSyncExternalStore } from "react";
import {
  configFromOrb,
  createDefaultConfig,
  createDefaultProject,
  createId,
  createSlide,
  categoryDockFromRoots,
  DEFAULT_CATEGORY_DOCK,
  featuredDockCategories,
  orbFromTreeRoot,
  syncDockWithRoots,
  HERO_BADGE_KINDS,
} from "./defaults";
import type {
  HeroAnimationPreset,
  HeroBadge,
  HeroBadgeKind,
  HeroBuilderConfig,
  HeroButton,
  HeroDesignProject,
  HeroOrbCategory,
  HeroPosition,
  HeroSlideDraft,
  MobileComposePreset,
  PreviewDevice,
  PublishedHeroPack,
} from "./types";

type Listener = () => void;
type PartialOrUpdater<T> = Partial<T> | ((state: T) => Partial<T> | T);
type SetFn<T> = (partial: PartialOrUpdater<T>, replace?: boolean) => void;
type GetFn<T> = () => T;

function create<T extends object>() {
  return (initializer: (set: SetFn<T>, get: GetFn<T>) => T) => {
    let state = {} as T;
    const listeners = new Set<Listener>();
    const get: GetFn<T> = () => state;
    const set: SetFn<T> = (partial, replace = false) => {
      const next = typeof partial === "function" ? partial(state) : partial;
      if (next === state) return;
      state = replace ? (next as T) : Object.assign({}, state, next);
      listeners.forEach((l) => l());
    };
    state = initializer(set, get);
    const useStore = (): T =>
      useSyncExternalStore(
        (onStoreChange) => {
          listeners.add(onStoreChange);
          return () => {
            listeners.delete(onStoreChange);
          };
        },
        () => state,
        () => state,
      );
    return useStore;
  };
}

function persist<T extends object>(
  config: (set: SetFn<T>, get: GetFn<T>) => T,
  options: {
    name: string;
    partialize: (s: T) => object;
    merge: (persisted: unknown, current: T) => T;
  },
) {
  return (set: SetFn<T>, get: GetFn<T>) => {
    const setAndPersist: SetFn<T> = (partial, replace) => {
      set(partial, replace);
      try {
        if (typeof window !== "undefined") {
          localStorage.setItem(options.name, JSON.stringify(options.partialize(get())));
        }
      } catch {
        /* ignore quota / private mode */
      }
    };
    const initial = config(setAndPersist, get);
    if (typeof window !== "undefined") {
      try {
        const raw = localStorage.getItem(options.name);
        if (raw) {
          return options.merge(JSON.parse(raw), initial);
        }
      } catch {
        /* ignore corrupt storage */
      }
    }
    return initial;
  };
}

const STORAGE_KEY = "karzar.admin.hero-builder.project.v3";

type TreeRootLike = {
  id: number;
  name: string;
  slug?: string | null;
  icon?: string | null;
  product_count?: number | null;
  parent_id?: number | null;
};

function snap(value: number, size: number, enabled: boolean): number {
  if (!enabled || size <= 0) return Math.min(100, Math.max(0, value));
  const stepped = Math.round(value / size) * size;
  return Math.min(100, Math.max(0, stepped));
}

function withSlideConfig(
  project: HeroDesignProject,
  slideId: string,
  updater: (config: HeroBuilderConfig) => HeroBuilderConfig,
): HeroDesignProject {
  return {
    ...project,
    slides: project.slides.map((s) =>
      s.id === slideId ? { ...s, config: updater(s.config) } : s,
    ),
  };
}

/** Keep featuredOrder as sparse slots 0–5 so empty slots stay empty. Dedup only. */
function densifyFeatured(categories: HeroOrbCategory[]): HeroOrbCategory[] {
  const claimed = new Map<number, string>();
  return categories.map((c) => {
    if (c.featuredOrder == null) return { ...c, featuredOrder: null };
    const slot = Math.max(0, Math.min(5, Math.floor(c.featuredOrder)));
    if (claimed.has(slot)) return { ...c, featuredOrder: null };
    claimed.set(slot, c.key);
    return { ...c, featuredOrder: slot };
  });
}

function firstEmptyFeaturedSlot(categories: HeroOrbCategory[]): number | null {
  const used = new Set(
    categories
      .map((c) => c.featuredOrder)
      .filter((n): n is number => n != null),
  );
  for (let i = 0; i < 6; i++) {
    if (!used.has(i)) return i;
  }
  return null;
}

interface HeroBuilderStore {
  project: HeroDesignProject;
  selectedLayerId: string | null;
  dirty: boolean;
  history: HeroDesignProject[];
  future: HeroDesignProject[];
  /** L1 categories available to add (computed on sync) */
  dockAvailable: TreeRootLike[];

  activeSlide: () => HeroSlideDraft | undefined;
  activeConfig: () => HeroBuilderConfig;

  setPreviewDevice: (device: PreviewDevice) => void;
  setMobilePreset: (preset: MobileComposePreset) => void;
  setSlideMobilePreset: (slideId: string, preset: MobileComposePreset) => void;
  setGrid: (patch: Partial<Pick<HeroDesignProject, "showGrid" | "snapToGrid" | "gridSize">>) => void;
  selectSlide: (id: string) => void;
  addSlide: () => void;
  duplicateSlide: (id: string) => void;
  removeSlide: (id: string) => void;
  renameSlide: (id: string, name: string) => void;
  setSlideActive: (id: string, isActive: boolean) => void;
  reorderSlide: (id: string, direction: -1 | 1) => void;

  updateOrb: (key: string, patch: Partial<HeroOrbCategory>) => void;
  setOrbFeaturedOrder: (key: string, featuredOrder: number | null) => void;
  assignFeaturedSlot: (key: string, slot: number) => void;
  moveFeaturedOrb: (key: string, direction: -1 | 1) => void;
  moveDockOrb: (key: string, direction: -1 | 1) => void;
  addOrbToDock: (root: TreeRootLike) => boolean;
  removeOrbFromDock: (key: string) => void;
  syncSlidesFromDock: () => void;
  syncCategoryDockFromRoots: (
    roots: TreeRootLike[],
    options?: { appendNew?: boolean },
  ) => { added: number; updated: number; removed: number; available: number };
  linkSlideToOrb: (slideId: string, orbKey: string | null) => void;

  selectLayer: (id: string | null) => void;
  moveLayer: (
    kind: "typography" | "button" | "badge" | "carousel",
    id: string | null,
    position: HeroPosition,
  ) => void;

  patchConfig: (patch: Partial<HeroBuilderConfig>) => void;
  setBackground: (patch: Partial<HeroBuilderConfig["background"]>) => void;
  setOverlay: (patch: Partial<HeroBuilderConfig["overlay"]>) => void;
  setTypography: (patch: Partial<HeroBuilderConfig["typography"]>) => void;
  setAnimation: (animation: HeroAnimationPreset) => void;
  setCarousel: (patch: Partial<HeroBuilderConfig["carousel"]>) => void;

  addButton: () => void;
  updateButton: (id: string, patch: Partial<HeroButton>) => void;
  removeButton: (id: string) => void;
  addBadge: (kind?: HeroBadgeKind) => void;
  updateBadge: (id: string, patch: Partial<HeroBadge>) => void;
  removeBadge: (id: string) => void;

  undo: () => void;
  redo: () => void;
  resetActive: () => void;
  importProject: (project: HeroDesignProject) => void;
  exportProjectJson: () => string;
  toPublishedPack: () => PublishedHeroPack;
  markClean: () => void;
}

function pushHistory(state: Pick<HeroBuilderStore, "project" | "history">) {
  return {
    history: [...state.history.slice(-24), state.project],
    future: [] as HeroDesignProject[],
    dirty: true,
  };
}

export const useHeroBuilderStore = create<HeroBuilderStore>()(
  persist(
    (set, get) => ({
      project: createDefaultProject(),
      selectedLayerId: "typography",
      dirty: false,
      history: [],
      future: [],
      dockAvailable: [],

      activeSlide: () => {
        const { project } = get();
        return project.slides.find((s) => s.id === project.activeSlideId) ?? project.slides[0];
      },

      activeConfig: () => get().activeSlide()?.config ?? createDefaultConfig(),

      setPreviewDevice: (device) =>
        set((s) => ({ project: { ...s.project, previewDevice: device } })),

      setMobilePreset: (mobilePreset) =>
        set((s) => ({
          ...pushHistory(s),
          project: { ...s.project, mobilePreset },
        })),

      setSlideMobilePreset: (slideId, mobilePreset) =>
        set((s) => ({
          ...pushHistory(s),
          project: {
            ...s.project,
            slides: s.project.slides.map((slide) =>
              slide.id === slideId ? { ...slide, mobilePreset } : slide,
            ),
            // Keep project default in sync with active slide for convenience
            mobilePreset:
              slideId === s.project.activeSlideId ? mobilePreset : s.project.mobilePreset,
          },
        })),

      setGrid: (patch) =>
        set((s) => ({ project: { ...s.project, ...patch } })),

      selectSlide: (id) =>
        set((s) => ({
          project: { ...s.project, activeSlideId: id },
          selectedLayerId: "typography",
        })),

      addSlide: () =>
        set((s) => {
          const slide = createSlide({
            name: `اسلاید ${s.project.slides.length + 1}`,
            sortOrder: s.project.slides.length + 1,
            mobilePreset: s.project.mobilePreset ?? "balanced",
          });
          return {
            ...pushHistory(s),
            project: {
              ...s.project,
              slides: [...s.project.slides, slide],
              activeSlideId: slide.id,
            },
            selectedLayerId: "typography",
          };
        }),

      duplicateSlide: (id) =>
        set((s) => {
          const source = s.project.slides.find((x) => x.id === id);
          if (!source) return s;
          const slide = createSlide({
            name: `${source.name} (کپی)`,
            sortOrder: s.project.slides.length + 1,
            mobilePreset: source.mobilePreset ?? s.project.mobilePreset,
            config: structuredClone(source.config),
          });
          return {
            ...pushHistory(s),
            project: {
              ...s.project,
              slides: [...s.project.slides, slide],
              activeSlideId: slide.id,
            },
          };
        }),

      removeSlide: (id) =>
        set((s) => {
          if (s.project.slides.length <= 1) return s;
          const slides = s.project.slides.filter((x) => x.id !== id);
          const activeSlideId =
            s.project.activeSlideId === id ? slides[0]!.id : s.project.activeSlideId;
          return {
            ...pushHistory(s),
            project: { ...s.project, slides, activeSlideId },
          };
        }),

      renameSlide: (id, name) =>
        set((s) => ({
          ...pushHistory(s),
          project: {
            ...s.project,
            slides: s.project.slides.map((x) => (x.id === id ? { ...x, name } : x)),
          },
        })),

      setSlideActive: (id, isActive) =>
        set((s) => ({
          ...pushHistory(s),
          project: {
            ...s.project,
            slides: s.project.slides.map((x) => (x.id === id ? { ...x, isActive } : x)),
          },
        })),

      reorderSlide: (id, direction) =>
        set((s) => {
          const list = [...s.project.slides].sort((a, b) => a.sortOrder - b.sortOrder);
          const idx = list.findIndex((x) => x.id === id);
          const swap = idx + direction;
          if (idx < 0 || swap < 0 || swap >= list.length) return s;
          const tmp = list[idx]!;
          list[idx] = list[swap]!;
          list[swap] = tmp;
          const slides = list.map((item, i) => ({ ...item, sortOrder: i + 1 }));
          return { ...pushHistory(s), project: { ...s.project, slides } };
        }),

      updateOrb: (key, patch) =>
        set((s) => {
          const dock = s.project.categoryDock ?? DEFAULT_CATEGORY_DOCK;
          return {
            ...pushHistory(s),
            project: {
              ...s.project,
              categoryDock: {
                categories: dock.categories.map((c) =>
                  c.key === key ? { ...c, ...patch } : c,
                ),
              },
            },
          };
        }),

      setOrbFeaturedOrder: (key, featuredOrder) =>
        set((s) => {
          const dock = s.project.categoryDock ?? DEFAULT_CATEGORY_DOCK;
          if (!dock.categories.some((c) => c.key === key)) return s;

          let nextOrder = featuredOrder;
          if (featuredOrder != null) {
            // Prefer an explicit slot; otherwise first empty 0–5.
            const empty = firstEmptyFeaturedSlot(
              dock.categories.filter((c) => c.key !== key),
            );
            if (featuredOrder < 0 || featuredOrder > 5) {
              nextOrder = empty;
            } else if (
              dock.categories.some(
                (c) => c.key !== key && c.featuredOrder === featuredOrder,
              )
            ) {
              // Requested slot taken — use first empty if available.
              nextOrder = empty ?? featuredOrder;
            }
            if (nextOrder == null) return s;
          }

          let categories = dock.categories.map((c) => {
            if (c.key === key) return { ...c, featuredOrder: nextOrder };
            if (nextOrder != null && c.featuredOrder === nextOrder) {
              return { ...c, featuredOrder: null };
            }
            return c;
          });

          categories = densifyFeatured(categories);
          return {
            ...pushHistory(s),
            project: { ...s.project, categoryDock: { categories } },
          };
        }),

      assignFeaturedSlot: (key, slot) =>
        set((s) => {
          const dock = s.project.categoryDock ?? DEFAULT_CATEGORY_DOCK;
          if (!dock.categories.some((c) => c.key === key)) return s;
          const target = Math.max(0, Math.min(5, Math.floor(slot)));
          const categories = densifyFeatured(
            dock.categories.map((c) => {
              if (c.key === key) return { ...c, featuredOrder: target };
              if (c.featuredOrder === target) return { ...c, featuredOrder: null };
              return c;
            }),
          );
          return {
            ...pushHistory(s),
            project: { ...s.project, categoryDock: { categories } },
          };
        }),

      moveFeaturedOrb: (key, direction) =>
        set((s) => {
          const dock = s.project.categoryDock ?? DEFAULT_CATEGORY_DOCK;
          const featured = featuredDockCategories(dock);
          const idx = featured.findIndex((c) => c.key === key);
          const swap = idx + direction;
          if (idx < 0 || swap < 0 || swap >= featured.length) return s;
          const a = featured[idx]!;
          const b = featured[swap]!;
          const orderA = a.featuredOrder;
          const orderB = b.featuredOrder;
          const categories = densifyFeatured(
            dock.categories.map((c) => {
              if (c.key === a.key) return { ...c, featuredOrder: orderB };
              if (c.key === b.key) return { ...c, featuredOrder: orderA };
              return c;
            }),
          );
          return {
            ...pushHistory(s),
            project: { ...s.project, categoryDock: { categories } },
          };
        }),

      moveDockOrb: (key, direction) =>
        set((s) => {
          const dock = s.project.categoryDock ?? DEFAULT_CATEGORY_DOCK;
          const list = [...dock.categories];
          const idx = list.findIndex((c) => c.key === key);
          const swap = idx + direction;
          if (idx < 0 || swap < 0 || swap >= list.length) return s;
          const tmp = list[idx]!;
          list[idx] = list[swap]!;
          list[swap] = tmp;
          return {
            ...pushHistory(s),
            project: { ...s.project, categoryDock: { categories: list } },
          };
        }),

      addOrbToDock: (root) => {
        let ok = false;
        set((s) => {
          const dock = s.project.categoryDock ?? DEFAULT_CATEGORY_DOCK;
          const exists = dock.categories.some(
            (c) =>
              c.categoryId === root.id ||
              c.key === (root.slug ?? `cat-${root.id}`) ||
              c.name.trim() === root.name.trim(),
          );
          if (exists) return s;
          const orb = orbFromTreeRoot(root, dock);
          ok = true;
          return {
            ...pushHistory(s),
            project: {
              ...s.project,
              categoryDock: { categories: [...dock.categories, orb] },
            },
            dockAvailable: s.dockAvailable.filter((r) => r.id !== root.id),
          };
        });
        return ok;
      },

      removeOrbFromDock: (key) =>
        set((s) => {
          const dock = s.project.categoryDock ?? DEFAULT_CATEGORY_DOCK;
          const removed = dock.categories.find((c) => c.key === key);
          if (!removed) return s;
          const categories = densifyFeatured(
            dock.categories.filter((c) => c.key !== key),
          );
          const availableExtra: TreeRootLike | null =
            removed.categoryId != null
              ? {
                  id: removed.categoryId,
                  name: removed.name,
                  slug: removed.slugHint || null,
                  icon: removed.icon,
                  product_count: removed.productCount,
                  parent_id: null,
                }
              : null;
          return {
            ...pushHistory(s),
            project: { ...s.project, categoryDock: { categories } },
            dockAvailable: availableExtra
              ? [...s.dockAvailable.filter((r) => r.id !== availableExtra.id), availableExtra]
              : s.dockAvailable,
          };
        }),

      syncSlidesFromDock: () =>
        set((s) => {
          const dock = s.project.categoryDock ?? DEFAULT_CATEGORY_DOCK;
          const featured = featuredDockCategories(dock);
          const slides = featured.map((orb, i) => {
            const existing = s.project.slides.find(
              (sl) => sl.config.linkedOrbKey === orb.key,
            );
            if (existing) {
              return {
                ...existing,
                name: orb.name,
                sortOrder: i + 1,
                config: {
                  ...existing.config,
                  linkedOrbKey: orb.key,
                  background: {
                    ...existing.config.background,
                    imageUrl: orb.heroImage,
                  },
                  typography: {
                    ...existing.config.typography,
                    title: orb.name,
                    subtitle: orb.subtitle,
                  },
                },
              };
            }
            return createSlide({
              name: orb.name,
              sortOrder: i + 1,
              mobilePreset: s.project.mobilePreset ?? "balanced",
              config: configFromOrb(orb),
            });
          });
          return {
            ...pushHistory(s),
            project: {
              ...s.project,
              slides,
              activeSlideId: slides[0]?.id ?? s.project.activeSlideId,
            },
          };
        }),

      syncCategoryDockFromRoots: (roots, options) => {
        let result = { added: 0, updated: 0, removed: 0, available: 0 };
        set((s) => {
          const prev = s.project.categoryDock ?? DEFAULT_CATEGORY_DOCK;
          // First-time / empty → full seed; otherwise smart merge
          const synced =
            !prev.categories.length
              ? (() => {
                  const dock = categoryDockFromRoots(roots, prev);
                  return {
                    dock,
                    available: [] as TreeRootLike[],
                    added: dock.categories.length,
                    updated: 0,
                    removed: 0,
                  };
                })()
              : syncDockWithRoots(roots, prev, {
                  appendNew: options?.appendNew ?? false,
                });

          result = {
            added: synced.added,
            updated: synced.updated,
            removed: synced.removed,
            available: synced.available.length,
          };

          const unchanged =
            synced.added === 0 &&
            synced.updated === 0 &&
            synced.removed === 0 &&
            JSON.stringify(synced.dock.categories.map((c) => c.key)) ===
              JSON.stringify(prev.categories.map((c) => c.key));

          if (unchanged) {
            return { dockAvailable: synced.available };
          }

          return {
            ...pushHistory(s),
            project: { ...s.project, categoryDock: synced.dock },
            dockAvailable: synced.available,
          };
        });
        return result;
      },

      linkSlideToOrb: (slideId, orbKey) =>
        set((s) => ({
          ...pushHistory(s),
          project: {
            ...s.project,
            slides: s.project.slides.map((slide) => {
              if (slide.id === slideId) {
                return {
                  ...slide,
                  config: { ...slide.config, linkedOrbKey: orbKey },
                };
              }
              if (orbKey && slide.config.linkedOrbKey === orbKey) {
                return {
                  ...slide,
                  config: { ...slide.config, linkedOrbKey: null },
                };
              }
              return slide;
            }),
          },
        })),

      selectLayer: (id) => set({ selectedLayerId: id }),

      moveLayer: (kind, id, position) =>
        set((s) => {
          const slideId = s.project.activeSlideId;
          const { snapToGrid, gridSize } = s.project;
          const nextPos = {
            x: snap(position.x, gridSize, snapToGrid),
            y: snap(position.y, gridSize, snapToGrid),
          };
          return {
            dirty: true,
            project: withSlideConfig(s.project, slideId, (config) => {
              if (kind === "typography") {
                return { ...config, typography: { ...config.typography, position: nextPos } };
              }
              if (kind === "carousel") {
                return { ...config, carousel: { ...config.carousel, position: nextPos } };
              }
              if (kind === "button" && id) {
                return {
                  ...config,
                  buttons: config.buttons.map((b) =>
                    b.id === id ? { ...b, position: nextPos } : b,
                  ),
                };
              }
              if (kind === "badge" && id) {
                return {
                  ...config,
                  badges: config.badges.map((b) =>
                    b.id === id ? { ...b, position: nextPos } : b,
                  ),
                };
              }
              return config;
            }),
          };
        }),

      patchConfig: (patch) =>
        set((s) => ({
          ...pushHistory(s),
          project: withSlideConfig(s.project, s.project.activeSlideId, (c) => ({
            ...c,
            ...patch,
          })),
        })),

      setBackground: (patch) =>
        set((s) => ({
          ...pushHistory(s),
          project: withSlideConfig(s.project, s.project.activeSlideId, (c) => ({
            ...c,
            background: { ...c.background, ...patch },
          })),
        })),

      setOverlay: (patch) =>
        set((s) => ({
          ...pushHistory(s),
          project: withSlideConfig(s.project, s.project.activeSlideId, (c) => ({
            ...c,
            overlay: { ...c.overlay, ...patch },
          })),
        })),

      setTypography: (patch) =>
        set((s) => ({
          ...pushHistory(s),
          project: withSlideConfig(s.project, s.project.activeSlideId, (c) => ({
            ...c,
            typography: { ...c.typography, ...patch },
          })),
        })),

      setAnimation: (animation) =>
        set((s) => ({
          ...pushHistory(s),
          project: withSlideConfig(s.project, s.project.activeSlideId, (c) => ({
            ...c,
            animation,
          })),
        })),

      setCarousel: (patch) =>
        set((s) => ({
          ...pushHistory(s),
          project: withSlideConfig(s.project, s.project.activeSlideId, (c) => ({
            ...c,
            carousel: { ...c.carousel, ...patch },
          })),
        })),

      addButton: () =>
        set((s) => ({
          ...pushHistory(s),
          selectedLayerId: "buttons",
          project: withSlideConfig(s.project, s.project.activeSlideId, (c) => ({
            ...c,
            buttons: [
              ...c.buttons,
              {
                id: createId("btn"),
                label: "دکمه جدید",
                variant: "solid" as const,
                bgColor: "#D02327",
                textColor: "#FFFFFF",
                borderRadius: 12,
                position: { x: 8, y: 80 },
                action: { type: "href" as const, value: "/catalog" },
                stylePreset: "primary" as const,
                sizePreset: "md" as const,
              },
            ],
          })),
        })),

      updateButton: (id, patch) =>
        set((s) => ({
          ...pushHistory(s),
          project: withSlideConfig(s.project, s.project.activeSlideId, (c) => ({
            ...c,
            buttons: c.buttons.map((b) => {
              if (b.id !== id) return b;
              return {
                ...b,
                ...patch,
                action: patch.action ? { ...b.action, ...patch.action } : b.action,
                position: patch.position ? { ...b.position, ...patch.position } : b.position,
              };
            }),
          })),
        })),

      removeButton: (id) =>
        set((s) => ({
          ...pushHistory(s),
          project: withSlideConfig(s.project, s.project.activeSlideId, (c) => ({
            ...c,
            buttons: c.buttons.filter((b) => b.id !== id),
          })),
        })),

      addBadge: (kind = "discount") => {
        const meta = HERO_BADGE_KINDS.find((k) => k.id === kind);
        set((s) => ({
          ...pushHistory(s),
          selectedLayerId: "badges",
          project: withSlideConfig(s.project, s.project.activeSlideId, (c) => ({
            ...c,
            badges: [
              ...c.badges,
              {
                id: createId("badge"),
                kind,
                style: "pill" as const,
                label: meta?.defaultLabel ?? "بج",
                meta: meta?.defaultMeta,
                position: { x: 8, y: 10 + c.badges.length * 8 },
                animated: true,
              },
            ],
          })),
        }));
      },

      updateBadge: (id, patch) =>
        set((s) => ({
          ...pushHistory(s),
          project: withSlideConfig(s.project, s.project.activeSlideId, (c) => ({
            ...c,
            badges: c.badges.map((b) => (b.id === id ? { ...b, ...patch } : b)),
          })),
        })),

      removeBadge: (id) =>
        set((s) => ({
          ...pushHistory(s),
          project: withSlideConfig(s.project, s.project.activeSlideId, (c) => ({
            ...c,
            badges: c.badges.filter((b) => b.id !== id),
          })),
        })),

      undo: () => {
        const { history, project, future } = get();
        if (!history.length) return;
        const prev = history[history.length - 1]!;
        set({
          project: prev,
          history: history.slice(0, -1),
          future: [project, ...future],
          dirty: true,
        });
      },

      redo: () => {
        const { future, project, history } = get();
        if (!future.length) return;
        const next = future[0]!;
        set({
          project: next,
          future: future.slice(1),
          history: [...history, project],
          dirty: true,
        });
      },

      resetActive: () =>
        set((s) => ({
          ...pushHistory(s),
          project: withSlideConfig(s.project, s.project.activeSlideId, () =>
            createDefaultConfig(),
          ),
        })),

      importProject: (project) =>
        set({ project, dirty: false, history: [], future: [], selectedLayerId: "typography" }),

      exportProjectJson: () => JSON.stringify(get().project, null, 2),

      toPublishedPack: (): PublishedHeroPack => {
        const { project } = get();
        const dock = project.categoryDock ?? DEFAULT_CATEGORY_DOCK;
        const categories = densifyFeatured(dock.categories);
        return {
          version: 1,
          publishedAt: new Date().toISOString(),
          categoryDock: { categories },
          mobilePreset: project.mobilePreset ?? "balanced",
          slides: [...project.slides]
            .filter((s) => s.isActive)
            .sort((a, b) => a.sortOrder - b.sortOrder)
            .map((s) => ({
              id: s.id,
              name: s.name,
              sortOrder: s.sortOrder,
              isActive: s.isActive,
              mobilePreset: s.mobilePreset ?? project.mobilePreset ?? "balanced",
              config: s.config,
            })),
        };
      },

      markClean: () => set({ dirty: false }),
    }),
    {
      name: STORAGE_KEY,
      partialize: (s) => ({ project: s.project }),
      merge: (persisted, current) => {
        const p = persisted as { project?: HeroDesignProject } | undefined;
        if (!p?.project) return current;
        return {
          ...current,
          project: {
            ...createDefaultProject(),
            ...p.project,
            categoryDock: p.project.categoryDock ?? DEFAULT_CATEGORY_DOCK,
            mobilePreset: p.project.mobilePreset ?? "balanced",
            slides: (p.project.slides ?? []).map((slide) => ({
              ...slide,
              mobilePreset: slide.mobilePreset ?? p.project?.mobilePreset ?? "balanced",
            })),
          },
        };
      },
    },
  ),
);
