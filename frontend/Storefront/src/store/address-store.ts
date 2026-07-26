"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

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

interface AddressState {
  addresses: SavedAddress[];
  addAddress: (input: AddressInput) => SavedAddress;
  updateAddress: (id: string, patch: Partial<AddressInput>) => void;
  removeAddress: (id: string) => void;
  setDefault: (id: string) => void;
  getDefault: () => SavedAddress | undefined;
  getById: (id: string) => SavedAddress | undefined;
}

function newId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `addr_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

export const useAddressStore = create<AddressState>()(
  persist(
    (set, get) => ({
      addresses: [],

      addAddress: (input) => {
        const makeDefault = input.is_default || get().addresses.length === 0;
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
        set((state) => ({
          addresses: [
            ...(makeDefault
              ? state.addresses.map((a) => ({ ...a, is_default: false }))
              : state.addresses),
            address,
          ],
        }));
        return address;
      },

      updateAddress: (id, patch) => {
        set((state) => {
          const next = state.addresses.map((a) => {
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
          return { addresses: next };
        });
      },

      removeAddress: (id) => {
        set((state) => {
          const filtered = state.addresses.filter((a) => a.id !== id);
          if (filtered.length > 0 && !filtered.some((a) => a.is_default)) {
            filtered[0] = { ...filtered[0], is_default: true };
          }
          return { addresses: filtered };
        });
      },

      setDefault: (id) => {
        set((state) => ({
          addresses: state.addresses.map((a) => ({
            ...a,
            is_default: a.id === id,
          })),
        }));
      },

      getDefault: () => get().addresses.find((a) => a.is_default) ?? get().addresses[0],

      getById: (id) => get().addresses.find((a) => a.id === id),
    }),
    { name: "karzar.addresses" },
  ),
);
