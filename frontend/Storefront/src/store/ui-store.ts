"use client";

import { create } from "zustand";

/** Ephemeral UI state: drawers, mobile menus, overlays. Never persisted. */
interface UiState {
  mobileMenuOpen: boolean;
  mobileCategoryOpen: boolean;
  filterDrawerOpen: boolean;
  megaMenuOpen: boolean;
  setMobileMenuOpen: (open: boolean) => void;
  setMobileCategoryOpen: (open: boolean) => void;
  setFilterDrawerOpen: (open: boolean) => void;
  setMegaMenuOpen: (open: boolean) => void;
}

export const useUiStore = create<UiState>((set) => ({
  mobileMenuOpen: false,
  mobileCategoryOpen: false,
  filterDrawerOpen: false,
  megaMenuOpen: false,
  setMobileMenuOpen: (open) => set({ mobileMenuOpen: open }),
  setMobileCategoryOpen: (open) => set({ mobileCategoryOpen: open }),
  setFilterDrawerOpen: (open) => set({ filterDrawerOpen: open }),
  setMegaMenuOpen: (open) => set({ megaMenuOpen: open }),
}));
