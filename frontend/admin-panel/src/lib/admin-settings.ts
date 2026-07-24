/** Client-side admin store settings (mock persistence until backend /settings exists). */

import { env } from "@/config/env";

export interface AdminStoreSettings {
  shop_name: string;
  support_phone: string;
  inquiry_enabled: boolean;
  min_order_note: string;
  /** When true, admin login requires password (recommended for production). */
  require_password_for_login: boolean;
}

export const DEFAULT_ADMIN_SETTINGS: AdminStoreSettings = {
  shop_name: "کارزار",
  support_phone: "۰۲۱۹۱۰۰۰۰۰۰۰",
  inquiry_enabled: true,
  min_order_note: "حداقل مبلغ سفارش: ۵۰۰٬۰۰۰ تومان",
  require_password_for_login: true,
};

const STORAGE_KEY = "karzar.admin.settings";

export function getAdminSettings(): AdminStoreSettings {
  if (typeof window === "undefined") return DEFAULT_ADMIN_SETTINGS;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_ADMIN_SETTINGS;
    return { ...DEFAULT_ADMIN_SETTINGS, ...JSON.parse(raw) };
  } catch {
    return DEFAULT_ADMIN_SETTINGS;
  }
}

export function saveAdminSettings(partial: Partial<AdminStoreSettings>): AdminStoreSettings {
  const next = { ...getAdminSettings(), ...partial };
  // Live mode always requires password — never persist optional-password for production.
  if (!env.USE_MOCK) {
    next.require_password_for_login = true;
  }
  if (typeof window !== "undefined") {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    window.dispatchEvent(new Event("karzar-admin-settings-change"));
  }
  return next;
}

/** Password is always required outside mock mode. */
export function isPasswordRequiredForLogin(): boolean {
  if (!env.USE_MOCK) return true;
  return getAdminSettings().require_password_for_login;
}
