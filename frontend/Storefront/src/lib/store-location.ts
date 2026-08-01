/**
 * Single source of truth for KarZar Tools storefront contact / map identity.
 * Street address matches existing contact + footer copy.
 * Map + routing: Neshan (نشان) place embed and directions.
 */

export const STORE_NAME = "KarZar Tools";
export const STORE_NAME_FA = "کارزار";

/** Visible Persian street address (already used on contact + footer). */
export const STORE_ADDRESS_FA =
  "تهران، امام خمینی، بین زندنژاد و مریخ، پاساژ فجر، پلاک ۱۰۸";

export const STORE_ADDRESS_LOCALITY = "تهران";
export const STORE_ADDRESS_COUNTRY = "IR";

/** Neshan place id for storefront location. */
export const STORE_NESHAN_PLACE_ID = "vbvELT2xOtSQ";

export const STORE_GEO = {
  latitude: 35.6869844,
  longitude: 51.4044884,
} as const;

/** Public Neshan place page (schema hasMap + address links). */
export const STORE_MAPS_URL = `https://neshan.org/maps/places/${STORE_NESHAN_PLACE_ID}`;

/**
 * Neshan routing from current location → store.
 * Web primary (`target=_blank`). Native deep-link pattern: `nshn:lat,lng`.
 */
export const STORE_NESHAN_DIRECTIONS_URL = `https://neshan.org/maps#/dir/currentLocation/${STORE_GEO.latitude},${STORE_GEO.longitude}`;

/** Neshan iframe embed src. */
export const STORE_NESHAN_EMBED_URL = `https://neshan.org/maps/iframe/places/${STORE_NESHAN_PLACE_ID}/${STORE_GEO.latitude}/${STORE_GEO.longitude}`;

/** Already published on contact + footer — not invented for this change. */
export const STORE_PHONE_DISPLAY = "09912480087";
export const STORE_PHONE_E164 = "+989912480087";
export const STORE_EMAIL = "info@karzartools.com";
