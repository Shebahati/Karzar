"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import {
  getVerifiedCustomerId,
  subscribeCustomerSession,
} from "@/lib/customer-session";

export interface SavedAddress {
  id: string;
  label: string;
  full_name: string;
  phone: string;
  province: string;
  city: string;
  postal_code: string;
  address_line: string;
  is_default: boolean;
}

export type AddressInput = Omit<SavedAddress, "id" | "is_default"> & {
  is_default?: boolean;
};

export const ADDRESS_PERSIST_KEY = "karzar.addresses";
const PERSIST_FORMAT_VERSION = 2;

type OwnerAddressMap = Record<string, SavedAddress[]>;

interface AddressState {
  byOwner: OwnerAddressMap;
  addresses: SavedAddress[];
  addAddress: (input: AddressInput) => SavedAddress;
  updateAddress: (id: string, patch: Partial<AddressInput>) => void;
  removeAddress: (id: string) => void;
  setDefault: (id: string) => void;
  getDefault: () => SavedAddress | undefined;
  getById: (id: string) => SavedAddress | undefined;
  clearVisibleAddresses: () => void;
  hydrateVisibleForVerifiedOwner: (ownerId: number) => void;
}

function newId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `addr_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

function ownerKey(ownerId: number): string {
  return String(ownerId);
}

function requireOwnerId(): number | null {
  return getVerifiedCustomerId();
}

function visibleAddresses(state: AddressState, ownerId: number | null): SavedAddress[] {
  if (ownerId == null) return [];
  return state.byOwner[ownerKey(ownerId)] ?? [];
}

function persistOwnerSlice(
  byOwner: OwnerAddressMap,
  ownerId: number,
  addresses: SavedAddress[],
): OwnerAddressMap {
  const key = ownerKey(ownerId);
  if (addresses.length === 0) {
    const next = { ...byOwner };
    delete next[key];
    return next;
  }
  return { ...byOwner, [key]: addresses };
}

function normalizePersistedByOwner(raw: OwnerAddressMap | undefined): OwnerAddressMap {
  if (!raw || typeof raw !== "object") return {};
  const next: OwnerAddressMap = {};
  for (const [key, list] of Object.entries(raw)) {
    if (!Array.isArray(list)) continue;
    next[key] = list.filter(
      (a) => a && typeof a.id === "string" && typeof a.full_name === "string",
    );
  }
  return next;
}

type AddressPersistSlice = Pick<AddressState, "byOwner">;

function migratePersistedState(persisted: unknown): AddressPersistSlice {
  if (!persisted || typeof persisted !== "object") {
    return { byOwner: {} };
  }
  if ("addresses" in persisted && !("byOwner" in persisted)) {
    return { byOwner: {} };
  }
  return {
    byOwner: normalizePersistedByOwner((persisted as AddressPersistSlice).byOwner),
  };
}

export function migrateAddressPersistForTests(persisted: unknown): AddressPersistSlice {
  return migratePersistedState(persisted);
}

export const useAddressStore = create<AddressState>()(
  persist(
    (set, get) => ({
      byOwner: {},
      addresses: [],

      clearVisibleAddresses: () => {
        set({ addresses: [] });
      },

      hydrateVisibleForVerifiedOwner: (ownerId: number) => {
        const owner = requireOwnerId();
        if (owner == null || owner !== ownerId) {
          set({ addresses: [] });
          return;
        }
        set({ addresses: visibleAddresses(get(), ownerId) });
      },

      addAddress: (input) => {
        const ownerId = requireOwnerId();
        if (ownerId == null) {
          throw new Error("ADDRESS_OWNER_REQUIRED");
        }
        const current = visibleAddresses(get(), ownerId);
        const makeDefault = input.is_default || current.length === 0;
        const address: SavedAddress = {
          id: newId(),
          label: input.label.trim() || "آدرس",
          full_name: input.full_name.trim(),
          phone: input.phone.trim(),
          province: input.province.trim(),
          city: input.city.trim(),
          postal_code: input.postal_code.trim(),
          address_line: input.address_line.trim(),
          is_default: makeDefault,
        };
        const nextList = [
          ...(makeDefault
            ? current.map((a) => ({ ...a, is_default: false }))
            : current),
          address,
        ];
        set((state) => ({
          addresses: nextList,
          byOwner: persistOwnerSlice(state.byOwner, ownerId, nextList),
        }));
        return address;
      },

      updateAddress: (id, patch) => {
        const ownerId = requireOwnerId();
        if (ownerId == null) return;
        set((state) => {
          const current = visibleAddresses(state, ownerId);
          const next = current.map((a) => {
            if (a.id !== id) {
              return patch.is_default ? { ...a, is_default: false } : a;
            }
            return {
              ...a,
              ...patch,
              label: patch.label != null ? patch.label.trim() || a.label : a.label,
              full_name: patch.full_name?.trim() ?? a.full_name,
              phone: patch.phone?.trim() ?? a.phone,
              province: patch.province?.trim() ?? a.province,
              city: patch.city?.trim() ?? a.city,
              postal_code: patch.postal_code?.trim() ?? a.postal_code,
              address_line: patch.address_line?.trim() ?? a.address_line,
              is_default: patch.is_default ?? a.is_default,
            };
          });
          return {
            addresses: next,
            byOwner: persistOwnerSlice(state.byOwner, ownerId, next),
          };
        });
      },

      removeAddress: (id) => {
        const ownerId = requireOwnerId();
        if (ownerId == null) return;
        set((state) => {
          const current = visibleAddresses(state, ownerId);
          const filtered = current.filter((a) => a.id !== id);
          if (filtered.length > 0 && !filtered.some((a) => a.is_default)) {
            filtered[0] = { ...filtered[0], is_default: true };
          }
          return {
            addresses: filtered,
            byOwner: persistOwnerSlice(state.byOwner, ownerId, filtered),
          };
        });
      },

      setDefault: (id) => {
        const ownerId = requireOwnerId();
        if (ownerId == null) return;
        set((state) => {
          const current = visibleAddresses(state, ownerId);
          const next = current.map((a) => ({
            ...a,
            is_default: a.id === id,
          }));
          return {
            addresses: next,
            byOwner: persistOwnerSlice(state.byOwner, ownerId, next),
          };
        });
      },

      getDefault: () => {
        const ownerId = requireOwnerId();
        if (ownerId == null) return undefined;
        const list = visibleAddresses(get(), ownerId);
        return list.find((a) => a.is_default) ?? list[0];
      },

      getById: (id) => {
        const ownerId = requireOwnerId();
        if (ownerId == null) return undefined;
        return visibleAddresses(get(), ownerId).find((a) => a.id === id);
      },
    }),
    {
      name: ADDRESS_PERSIST_KEY,
      version: PERSIST_FORMAT_VERSION,
      migrate: (persisted) => migratePersistedState(persisted),
      skipHydration: true,
      partialize: (state): AddressPersistSlice => ({ byOwner: state.byOwner }),
      merge: (persisted, current) => {
        const slice = migratePersistedState(persisted);
        return {
          ...current,
          byOwner: slice.byOwner,
          addresses: [],
        };
      },
    },
  ),
);

if (typeof window !== "undefined") {
  subscribeCustomerSession(() => {
    if (getVerifiedCustomerId() == null) {
      useAddressStore.getState().clearVisibleAddresses();
    }
  });
}
