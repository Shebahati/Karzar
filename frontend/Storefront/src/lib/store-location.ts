/**
 * Single source of truth for KarZar Tools storefront contact / map identity.
 * Street address matches existing contact + footer copy; Maps place is the
 * official Google listing (g/11ntgsmq22). Do not invent hours here.
 */

export const STORE_NAME = "KarZar Tools";
export const STORE_NAME_FA = "کارزار";

/** Visible Persian street address (already used on contact + footer). */
export const STORE_ADDRESS_FA =
  "تهران، امام خمینی، بین زندنژاد و مریخ، پاساژ فجر، پلاک ۱۰۸";

export const STORE_ADDRESS_LOCALITY = "تهران";
export const STORE_ADDRESS_COUNTRY = "IR";

/** Official Google Maps place (KarZar Tools). */
export const STORE_MAPS_URL =
  "https://www.google.com/maps/place/KarZar+Tools/@35.6873,51.40428,17z/data=!3m1!4b1!4m6!3m5!1s0x3f8e01002501921b:0xf1af8e0b47b31b9f!8m2!3d35.6873!4d51.40428!16s%2Fg%2F11ntgsmq22";

/** Lazy iframe embed pinned to place coordinates (no Maps Embed API key). */
export const STORE_MAPS_EMBED_URL =
  "https://www.google.com/maps?q=35.6873,51.40428&z=17&hl=fa&output=embed";

export const STORE_GEO = {
  latitude: 35.6873,
  longitude: 51.40428,
} as const;

/** Already published on contact + footer — not invented for this change. */
export const STORE_PHONE_DISPLAY = "09912480087";
export const STORE_PHONE_E164 = "+989912480087";
export const STORE_EMAIL = "info@karzartools.com";
