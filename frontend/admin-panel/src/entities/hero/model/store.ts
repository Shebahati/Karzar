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
  createEmptySlideSlot,
  createId,
  createSlide,
  categoryDockFromRoots,
  DEFAULT_CATEGORY_DOCK,
  densifyFeaturedOrders,
  featuredDockCategories,
  featuredIndexForSlide,
  firstEmptyFeaturedSlot,
  HERO_FEATURED_SLOT_COUNT,
  HERO_SLIDE_SLOT_COUNT,
  isSlideFilled,
  isSpecialDockOrb,
  normalizeHeroProject,
  orbFromTreeRoot,
  syncDockWithRoots,
  validateHeroProject,
  HERO_BADGE_KINDS,
} from "./defaults";
import type {
  HeroAnimationPreset,
  HeroBadge,
  HeroBadgeKind,
  HeroBuilderConfig,
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

/** Bump key so stale 13-slide local drafts remigrate through normalize. */
const STORAGE_KEY = "karzar.admin.hero-builder.project.v4";

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
      s.id === slideId ? { ...s, config: updater(s.config), isPlaceholder: false } : s,
    ),
  };
}

function clampFeaturedSlot(slot: number): number {
  return Math.max(0, Math.min(HERO_FEATURED_SLOT_COUNT - 1, Math.floor(slot)));
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
  validationIssues: () => ReturnType<typeof validateHeroProject>;
  canPublish: () => boolean;
  featuredOrbIndexForActive: () => number;

  setPreviewDevice: (device: PreviewDevice) => void;
  setMobilePreset: (preset: MobileComposePreset) => void;
  setSlideMobilePreset: (slideId: string, preset: MobileComposePreset) => void;
  setGrid: (patch: Partial<Pick<HeroDesignProject, "showGrid" | "snapToGrid" | "gridSize">>) => void;
  selectSlide: (id: string) => void;
  /** Fill first empty hex slot — no-op at 6 filled. */
  addSlide: () => boolean;
  duplicateSlide: (id: string) => boolean;
  /** Clear slot to placeholder (keeps fixed 6 + stable id). */
  removeSlide: (id: string) => void;
  fillSlideFromOrb: (slideId: string, orb: HeroOrbCategory) => void;
  fillSlideFromCurated: (slideId: string, config: HeroBuilderConfig, name: string) => void;
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
  /** Refresh content of slides already linked by orb key — never rebuild by index. */
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
  updateButton: (id: string, patch: Partial<HeroButtonLoose>) => void;
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

type HeroButtonLoose = HeroBuilderConfig["buttons"][number];

function pushHistory(state: Pick<HeroBuilderStore, "project" | "history">) {
  return {
    history: [...state.history.slice(-24), state.project],
    future: [] as HeroDesignProject[],
    dirty: true,
  };
}

function firstEmptySlot(slides: HeroSlideDraft[]): HeroSlideDraft | undefined {
  return [...slides]
    .sort((a, b) => a.sortOrder - b.sortOrder)
    .find((s) => s.isPlaceholder || !isSlideFilled(s));
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

      validationIssues: () => validateHeroProject(get().project),

      canPublish: () => validateHeroProject(get().project).length === 0,

      featuredOrbIndexForActive: () => {
        const { project } = get();
        const slide = project.slides.find((s) => s.id === project.activeSlideId);
        return featuredIndexForSlide(slide, project.categoryDock ?? DEFAULT_CATEGORY_DOCK);
      },

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

      addSlide: () => {
        let ok = false;
        set((s) => {
          const empty = firstEmptySlot(s.project.slides);
          if (!empty) return s;
          const slide = createSlide({
            id: empty.id,
            name: `اسلاید ${empty.sortOrder}`,
            sortOrder: empty.sortOrder,
            mobilePreset: s.project.mobilePreset ?? "balanced",
            isActive: true,
            isPlaceholder: false,
          });
          ok = true;
          return {
            ...pushHistory(s),
            project: {
              ...s.project,
              slides: s.project.slides.map((x) => (x.id === empty.id ? slide : x)),
              activeSlideId: slide.id,
            },
            selectedLayerId: "typography",
          };
        });
        return ok;
      },

      duplicateSlide: (id) => {
        let ok = false;
        set((s) => {
          const source = s.project.slides.find((x) => x.id === id);
          const empty = firstEmptySlot(s.project.slides.filter((x) => x.id !== id));
          if (!source || source.isPlaceholder || !empty) return s;
          const slide: HeroSlideDraft = {
            ...createSlide({
              id: empty.id,
              name: `${source.name} (کپی)`,
              sortOrder: empty.sortOrder,
              mobilePreset: source.mobilePreset ?? s.project.mobilePreset,
              config: structuredClone(source.config),
              isActive: true,
              isPlaceholder: false,
            }),
            config: {
              ...structuredClone(source.config),
              // Avoid duplicate orb binding — admin re-links explicitly.
              linkedOrbKey: null,
            },
          };
          ok = true;
          return {
            ...pushHistory(s),
            project: {
              ...s.project,
              slides: s.project.slides.map((x) => (x.id === empty.id ? slide : x)),
              activeSlideId: slide.id,
            },
          };
        });
        return ok;
      },

      removeSlide: (id) =>
        set((s) => {
          const target = s.project.slides.find((x) => x.id === id);
          if (!target) return s;
          const cleared = createEmptySlideSlot(target.sortOrder - 1);
          // Keep stable id so dock mappings / history don't scramble.
          const slot: HeroSlideDraft = { ...cleared, id: target.id, sortOrder: target.sortOrder };
          const slides = s.project.slides.map((x) => (x.id === id ? slot : x));
          return {
            ...pushHistory(s),
            project: {
              ...s.project,
              slides,
              activeSlideId:
                s.project.activeSlideId === id
                  ? slides.find((x) => isSlideFilled(x))?.id ?? slides[0]!.id
                  : s.project.activeSlideId,
            },
          };
        }),

      fillSlideFromOrb: (slideId, orb) =>
        set((s) => ({
          ...pushHistory(s),
          project: {
            ...s.project,
            slides: s.project.slides.map((slide) => {
              if (slide.id === slideId) {
                return {
                  ...slide,
                  name: orb.name,
                  isActive: true,
                  isPlaceholder: false,
                  config: configFromOrb(orb),
                };
              }
              if (slide.config.linkedOrbKey === orb.key) {
                return {
                  ...slide,
                  config: { ...slide.config, linkedOrbKey: null },
                };
              }
              return slide;
            }),
            activeSlideId: slideId,
          },
        })),

      fillSlideFromCurated: (slideId, config, name) =>
        set((s) => ({
          ...pushHistory(s),
          project: {
            ...s.project,
            slides: s.project.slides.map((slide) => {
              if (slide.id !== slideId) {
                if (
                  config.linkedOrbKey &&
                  slide.config.linkedOrbKey === config.linkedOrbKey
                ) {
                  return {
                    ...slide,
                    config: { ...slide.config, linkedOrbKey: null },
                  };
                }
                return slide;
              }
              return {
                ...slide,
                name,
                isActive: true,
                isPlaceholder: false,
                config: structuredClone(config),
              };
            }),
            activeSlideId: slideId,
          },
        })),

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
            slides: s.project.slides.map((x) =>
              x.id === id && !x.isPlaceholder ? { ...x, isActive } : x,
            ),
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
            const empty = firstEmptyFeaturedSlot(
              dock.categories.filter((c) => c.key !== key),
            );
            if (
              featuredOrder < 0 ||
              featuredOrder >= HERO_FEATURED_SLOT_COUNT
            ) {
              nextOrder = empty;
            } else if (
              dock.categories.some(
                (c) => c.key !== key && c.featuredOrder === featuredOrder,
              )
            ) {
              nextOrder = empty ?? featuredOrder;
            }
            if (nextOrder == null) return s;
            nextOrder = clampFeaturedSlot(nextOrder);
          }

          let categories = dock.categories.map((c) => {
            if (c.key === key) return { ...c, featuredOrder: nextOrder };
            if (nextOrder != null && c.featuredOrder === nextOrder) {
              return { ...c, featuredOrder: null };
            }
            return c;
          });

          categories = densifyFeaturedOrders(categories);
          return {
            ...pushHistory(s),
            project: { ...s.project, categoryDock: { categories } },
          };
        }),

      assignFeaturedSlot: (key, slot) =>
        set((s) => {
          const dock = s.project.categoryDock ?? DEFAULT_CATEGORY_DOCK;
          if (!dock.categories.some((c) => c.key === key)) return s;
          const target = clampFeaturedSlot(slot);
          const categories = densifyFeaturedOrders(
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
          const categories = densifyFeaturedOrders(
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
          if (!removed || isSpecialDockOrb(removed)) return s;
          const categories = densifyFeaturedOrders(
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
            project: {
              ...s.project,
              categoryDock: { categories },
              // Drop orphan slide↔orb links (id-stable slides keep their slot).
              slides: s.project.slides.map((slide) =>
                slide.config.linkedOrbKey === key
                  ? { ...slide, config: { ...slide.config, linkedOrbKey: null } }
                  : slide,
              ),
            },
            dockAvailable: availableExtra
              ? [...s.dockAvailable.filter((r) => r.id !== availableExtra.id), availableExtra]
              : s.dockAvailable,
          };
        }),

      syncSlidesFromDock: () =>
        set((s) => {
          const dock = s.project.categoryDock ?? DEFAULT_CATEGORY_DOCK;
          // Id-safe refresh: only update slides already linked to an orb key.
          // Never rebuild the slide array from featuredOrder indices.
          const slides = s.project.slides.map((slide) => {
            const key = slide.config.linkedOrbKey;
            if (!key || slide.isPlaceholder) return slide;
            const orb = dock.categories.find((c) => c.key === key);
            if (!orb) return slide;
            return {
              ...slide,
              name: orb.name || slide.name,
              config: {
                ...slide.config,
                linkedOrbKey: orb.key,
                background: {
                  ...slide.config.background,
                  imageUrl: orb.heroImage || slide.config.background.imageUrl,
                },
                typography: {
                  ...slide.config.typography,
                  subtitle: orb.subtitle || slide.config.typography.subtitle,
                },
              },
            };
          });
          return {
            ...pushHistory(s),
            project: { ...s.project, slides },
          };
        }),

      syncCategoryDockFromRoots: (roots, options) => {
        let result = { added: 0, updated: 0, removed: 0, available: 0 };
        set((s) => {
          const prev = s.project.categoryDock ?? DEFAULT_CATEGORY_DOCK;
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

          const validKeys = new Set(synced.dock.categories.map((c) => c.key));
          const slides = s.project.slides.map((slide) => {
            const key = slide.config.linkedOrbKey;
            if (key && !validKeys.has(key)) {
              return { ...slide, config: { ...slide.config, linkedOrbKey: null } };
            }
            return slide;
          });

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
            project: { ...s.project, categoryDock: synced.dock, slides },
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
                  isPlaceholder: false,
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
          project: normalizeHeroProject(prev),
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
          project: normalizeHeroProject(next),
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
        set({
          project: normalizeHeroProject(project),
          dirty: false,
          history: [],
          future: [],
          selectedLayerId: "typography",
        }),

      exportProjectJson: () => JSON.stringify(get().project, null, 2),

      toPublishedPack: (): PublishedHeroPack => {
        const project = normalizeHeroProject(get().project);
        const dock = project.categoryDock ?? DEFAULT_CATEGORY_DOCK;
        const categories = densifyFeaturedOrders(dock.categories);
        return {
          version: 1,
          publishedAt: new Date().toISOString(),
          categoryDock: { categories },
          mobilePreset: project.mobilePreset ?? "balanced",
          slides: [...project.slides]
            .filter((s) => !s.isPlaceholder && s.isActive && isSlideFilled(s))
            .sort((a, b) => a.sortOrder - b.sortOrder)
            .slice(0, HERO_SLIDE_SLOT_COUNT)
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
          project: normalizeHeroProject({
            ...createDefaultProject(),
            ...p.project,
            categoryDock: p.project.categoryDock ?? DEFAULT_CATEGORY_DOCK,
            mobilePreset: p.project.mobilePreset ?? "balanced",
            slides: p.project.slides ?? [],
          }),
        };
      },
    },
  ),
);
