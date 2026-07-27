/**
 * Single source of truth for KarZar Tools storefront contact / map identity.
 * Street address matches existing contact + footer copy.
 * External map links are intentionally excluded from customer-facing content.
 */

export const STORE_NAME = "KarZar Tools";
export const STORE_NAME_FA = "کارزار";

/** Visible Persian street address (already used on contact + footer). */
export const STORE_ADDRESS_FA =
  "تهران، امام خمینی، بین زندنژاد و مریخ، پاساژ فجر، پلاک ۱۰۸";

export const STORE_ADDRESS_LOCALITY = "تهران";
export const STORE_ADDRESS_COUNTRY = "IR";

/** Internal contact anchor for storefront address access. */
export const STORE_MAPS_URL = "/contact#store-address";

/** Local map placeholder asset (no third-party embeds). */
export const STORE_MAPS_EMBED_URL = "/images/placeholders/store-location-map.svg";

export const STORE_GEO = {
  latitude: 35.6873,
  longitude: 51.40428,
} as const;

/** Already published on contact + footer — not invented for this change. */
export const STORE_PHONE_DISPLAY = "09912480087";
export const STORE_PHONE_E164 = "+989912480087";
export const STORE_EMAIL = "info@karzartools.com";
