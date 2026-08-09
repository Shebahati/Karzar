/**
 * Single source of truth for KarZar Tools storefront contact / map identity.
 * STORE_ADDRESS_FA is the company/seller street address for UI + PDFs + JSON-LD.
 * Map + routing: Neshan (نشان) place embed and directions.
 */

export const STORE_NAME = "KarZar Tools";
export const STORE_NAME_FA = "کارزار";

/** Visible Persian street address (contact, footer, invoice/proforma PDFs, JSON-LD). */
export const STORE_ADDRESS_FA =
  "تهران، خیابان امام خمینی، حدفاصل میدان حسن‌آباد و تقاطع ولی‌عصر، مجتمع تجاری فجر، پلاک ۱۰۸";

/** Short map-panel caption (building + plaque + map provider). */
export const STORE_ADDRESS_MAP_CAPTION_FA =
  "مجتمع تجاری فجر، پلاک ۱۰۸ · نشان";

export const STORE_ADDRESS_LOCALITY = "تهران";
export const STORE_ADDRESS_COUNTRY = "IR";

/** Neshan place id for storefront location. */
export const STORE_NESHAN_PLACE_ID = "bf220a8c1cf5f0240b6587c9e6f98197";

export const STORE_GEO = {
  latitude: 35.68701695469828,
  longitude: 51.404487515344236,
} as const;

/** Public Neshan place page (schema hasMap + address links). */
export const STORE_MAPS_URL = `https://neshan.org/maps/places/${STORE_NESHAN_PLACE_ID}`;

/**
 * Neshan routing from current location → store.
 * Web primary (`target=_blank`). Native deep-link pattern: `nshn:lat,lng`.
 */
export const STORE_NESHAN_DIRECTIONS_URL = `https://neshan.org/maps#/dir/currentLocation/${STORE_GEO.latitude},${STORE_GEO.longitude}`;

/** Neshan iframe embed src (place + camera hash from Neshan share). */
export const STORE_NESHAN_EMBED_URL = `https://neshan.org/maps/iframe/places/${STORE_NESHAN_PLACE_ID}#c35.687-51.405-20z-0p/${STORE_GEO.latitude}/${STORE_GEO.longitude}`;

/** Already published on contact + footer — not invented for this change. */
export const STORE_PHONE_DISPLAY = "09912480087";
export const STORE_PHONE_E164 = "+989912480087";
export const STORE_EMAIL = "info@karzartools.com";

/** Live Telegram support — @Karzar_support1 */
export const STORE_TELEGRAM_URL = "https://t.me/Karzar_support1";

/** Live WhatsApp support — +98 991 248 0087 */
export const STORE_WHATSAPP_URL = "https://wa.me/989912480087";

/** Live Instagram — @karzartools */
export const STORE_INSTAGRAM_URL = "https://www.instagram.com/karzartools/";
