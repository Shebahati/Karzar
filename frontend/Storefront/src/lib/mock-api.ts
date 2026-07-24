/**
 * In-memory mock API.
 *
 * Every function returns a Promise resolved after `env.MOCK_LATENCY_MS` to mimic
 * real network behavior. The service layer (`src/services/*`) decides — based on
 * `env.USE_MOCK` — whether to call these or the real Axios client, so swapping
 * to the live backend requires only an env-var change, no code edits.
 */

import { env } from "@/config/env";
import { sleep } from "@/lib/utils";
import {
  buildCategoryTree,
  collectDescendantIds,
  enrichCategories,
} from "@/lib/category-tree";
import {
  BLOG_POSTS,
  BRANDS,
  CATEGORIES,
  COMMENTS,
  HERO_SLIDES,
  PRODUCTS,
} from "@/data/mock-data";
import type { Brand, CategoryFlat, CategoryTreeNode } from "@/types/category";
import type { Article, BlogPost, HeroSlide, ProductComment } from "@/types/content";
import type {
  CheckoutPayload,
  CheckoutResponse,
} from "@/types/checkout";
import type { ContactValues } from "@/lib/validation";
import { buildOrderTimeline } from "@/lib/order-timeline";
import { ORDER_STATUS_LABELS } from "@/lib/constants";
import type { CategoryBrief, ProductDetail, ProductListParams, ProductListResponse, ProductSummary } from "@/types/product";
import type {
  MeResponse,
  OtpRequestPayload,
  OtpRequestResponse,
  OtpVerifyPayload,
  OtpVerifyResponse,
} from "@/types/auth";
import type {
  OrderListResponse,
  OrderTracking,
} from "@/types/order";
import type {
  PaymentInitPayload,
  PaymentInitResponse,
  PaymentVerifyPayload,
  PaymentVerifyResponse,
} from "@/types/payment";
import type { SpecFilterOptions } from "@/types/spec-filter";

const flat: CategoryFlat[] = enrichCategories(CATEGORIES);
const flatById = new Map(flat.map((c) => [c.id, c]));

type MockOrder = {
  order_id: number;
  tracking_code: string;
  mode: CheckoutPayload["mode"];
  status: CheckoutResponse["status"];
  status_label: string;
  estimated_total: string | null;
  created_at: string;
  customer_phone: string;
  customer_name: string;
  postal_tracking_code?: string | null;
  delivery_eta?: string | null;
  items: Array<{ product_id: number; quantity: number; unit_price: string | null }>;
};

const MOCK_ORDERS_KEY = "karzar.mock.orders";
const MOCK_PAYMENTS_KEY = "karzar.mock.payments";

/** Persist checkout/payment maps so full-page gateway redirects survive reload. */
function loadMockMap<V>(key: string): Map<string, V> {
  if (typeof window === "undefined") return new Map();
  try {
    const raw = sessionStorage.getItem(key);
    if (!raw) return new Map();
    const entries = JSON.parse(raw) as [string, V][];
    return new Map(entries);
  } catch {
    return new Map();
  }
}

function saveMockMap<V>(key: string, map: Map<string | number, V>) {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(key, JSON.stringify([...map.entries()]));
  } catch {
    /* ignore quota */
  }
}

/** In-memory (+ session) mock orders for payment / tracking flows. */
const mockOrders = new Map<number, MockOrder>(
  [...loadMockMap<MockOrder>(MOCK_ORDERS_KEY).entries()].map(([k, v]) => [
    Number(k),
    v,
  ]),
);

const mockPayments = loadMockMap<{ order_id: number; authority: string }>(
  MOCK_PAYMENTS_KEY,
);

function persistOrders() {
  saveMockMap(MOCK_ORDERS_KEY, mockOrders);
}

function persistPayments() {
  saveMockMap(MOCK_PAYMENTS_KEY, mockPayments);
}

/** Mock session — tracks logged-in customer for order filtering. */
const mockSession = {
  phone: "09121234567",
  full_name: "کاربر آزمایشی" as string | null,
  id: 1,
};

function stockStatus(p: (typeof PRODUCTS)[number]): string {
  if (!p.availability || Number(p.stock_quantity) <= 0) return "ناموجود";
  if (p.low_stock) return "موجودی محدود";
  return "موجود";
}

function categoryBrief(categoryId: number | null): CategoryBrief | null {
  if (categoryId == null) return null;
  const c = flatById.get(categoryId);
  if (!c) return null;
  return {
    id: c.id,
    name: c.name,
    breadcrumb: c.breadcrumb,
    hierarchy_label: c.breadcrumb.join(" › "),
  };
}

function brandBrief(brandId: number | null) {
  if (brandId == null) return null;
  const b = BRANDS.find((x) => x.id === brandId);
  if (!b) return null;
  return { id: b.id, name: b.name, country: b.country ?? null };
}

function toSummary(p: (typeof PRODUCTS)[number]): ProductSummary {
  return {
    id: p.id,
    sku: p.sku,
    name: p.name,
    thumbnail: p.thumbnail,
    base_price: p.base_price,
    original_price: p.original_price,
    discount_percent: p.discount_percent,
    stock_status: stockStatus(p),
    availability: p.availability,
    is_original: p.is_original,
    category: categoryBrief(p.category_id),
    brand: brandBrief(p.brand_id),
  };
}

function toDetail(p: (typeof PRODUCTS)[number]): ProductDetail {
  return {
    ...p,
    stock_status: stockStatus(p),
    category: categoryBrief(p.category_id),
    brand: brandBrief(p.brand_id),
  };
}

export const mockApi = {
  async listCategoriesTree(): Promise<CategoryTreeNode[]> {
    await sleep(env.MOCK_LATENCY_MS);
    return buildCategoryTree(CATEGORIES);
  },

  async listCategoriesFlat(): Promise<CategoryFlat[]> {
    await sleep(env.MOCK_LATENCY_MS);
    return flat;
  },

  async listBrands(): Promise<Brand[]> {
    await sleep(env.MOCK_LATENCY_MS);
    return BRANDS;
  },

  async listProducts(params: ProductListParams = {}): Promise<ProductListResponse> {
    await sleep(env.MOCK_LATENCY_MS);
    let items = PRODUCTS.filter((p) => p.is_active);

    if (params.category_id != null) {
      const ids = new Set(collectDescendantIds(CATEGORIES, params.category_id));
      items = items.filter((p) => p.category_id != null && ids.has(p.category_id));
    }
    if (params.brand_ids?.length) {
      const allowed = new Set(params.brand_ids);
      items = items.filter((p) => p.brand_id != null && allowed.has(p.brand_id));
    }
    if (params.countries?.length) {
      const allowedCountries = new Set(params.countries);
      const brandIds = new Set(
        BRANDS.filter((b) => b.country != null && allowedCountries.has(b.country)).map(
          (b) => b.id,
        ),
      );
      items = items.filter((p) => p.brand_id != null && brandIds.has(p.brand_id));
    }
    if (params.in_stock === true) {
      items = items.filter((p) => p.availability && Number(p.stock_quantity) > 0);
    } else if (params.in_stock === false) {
      items = items.filter((p) => !p.availability || Number(p.stock_quantity) <= 0);
    }
    if (params.search) {
      const q = params.search.trim().toLowerCase();
      items = items.filter((p) => {
        const brandName =
          BRANDS.find((b) => b.id === p.brand_id)?.name?.toLowerCase() ?? "";
        return (
          p.name.toLowerCase().includes(q) ||
          p.sku.toLowerCase().includes(q) ||
          brandName.includes(q)
        );
      });
    }
    if (params.min_price != null) {
      items = items.filter(
        (p) => p.base_price != null && Number(p.base_price) >= params.min_price!,
      );
    }
    if (params.max_price != null) {
      items = items.filter(
        (p) => p.base_price != null && Number(p.base_price) <= params.max_price!,
      );
    }

    if (params.spec_filters) {
      for (const [path, expected] of Object.entries(params.spec_filters)) {
        if (!expected) continue;
        items = items.filter((p) => {
          if (path.startsWith("technical_specs.")) {
            const key = path.slice("technical_specs.".length);
            const arr = p.specifications?.technical_specs ?? [];
            const row = arr.find((x) => x.key === key);
            return row?.value?.toLowerCase() === expected.toLowerCase();
          }
          const parts = path.split(".");
          let cursor: unknown = p.specifications;
          for (const part of parts) {
            if (cursor == null || typeof cursor !== "object") return false;
            cursor = (cursor as Record<string, unknown>)[part];
          }
          return String(cursor ?? "").toLowerCase() === expected.toLowerCase();
        });
      }
    }

    const priceOf = (v: string | null) => (v == null ? 0 : Number(v));
    switch (params.sort) {
      case "price_asc":
        items = [...items].sort((a, b) => priceOf(a.base_price) - priceOf(b.base_price));
        break;
      case "price_desc":
        items = [...items].sort((a, b) => priceOf(b.base_price) - priceOf(a.base_price));
        break;
      case "discount_desc":
        items = [...items].sort((a, b) => (b.discount_percent ?? 0) - (a.discount_percent ?? 0));
        break;
      case "stock_first":
        items = [...items].sort((a, b) => {
          const aStock = a.availability ? 1 : 0;
          const bStock = b.availability ? 1 : 0;
          if (bStock !== aStock) return bStock - aStock;
          return b.id - a.id;
        });
        break;
      case "name_asc":
        items = [...items].sort((a, b) => a.name.localeCompare(b.name, "fa"));
        break;
      case "name_desc":
        items = [...items].sort((a, b) => b.name.localeCompare(a.name, "fa"));
        break;
      case "newest":
      default:
        items = [...items].sort((a, b) => b.id - a.id);
    }

    const total = items.length;
    const skip = params.skip ?? 0;
    const limit = params.limit ?? 12;
    const page = items.slice(skip, skip + limit);

    return {
      data: page.map(toSummary),
      meta: {
        total_count: total,
        skip,
        limit,
        has_next: skip + limit < total,
        has_prev: skip > 0,
      },
    };
  },

  async getProduct(id: number): Promise<ProductDetail> {
    await sleep(env.MOCK_LATENCY_MS);
    const p = PRODUCTS.find((x) => x.id === id);
    if (!p) throw new Error("محصول یافت نشد.");
    return toDetail(p);
  },

  async getRelatedProducts(id: number): Promise<ProductSummary[]> {
    await sleep(env.MOCK_LATENCY_MS);
    const target = PRODUCTS.find((x) => x.id === id);
    if (!target) return [];
    const sameParent = (cid: number | null) => {
      const c = cid != null ? flatById.get(cid) : undefined;
      return c?.ancestor_ids[c.ancestor_ids.length - 1];
    };
    const targetParent = sameParent(target.category_id);
    return PRODUCTS.filter(
      (p) => p.id !== id && p.is_active && sameParent(p.category_id) === targetParent,
    )
      .slice(0, 6)
      .map(toSummary);
  },

  async listComments(productId: number): Promise<ProductComment[]> {
    await sleep(env.MOCK_LATENCY_MS);
    return COMMENTS.filter((c) => c.product_id === productId);
  },

  async listArticles(): Promise<Article[]> {
    await sleep(env.MOCK_LATENCY_MS);
    // Teasers are derived from the blog posts to keep a single source of truth.
    return BLOG_POSTS.map(
      ({ id, slug, title, excerpt, cover_image, published_at, reading_minutes }) => ({
        id,
        slug,
        title,
        excerpt,
        cover_image,
        published_at,
        reading_minutes,
      }),
    );
  },

  async getArticle(slug: string): Promise<BlogPost> {
    await sleep(env.MOCK_LATENCY_MS);
    const post = BLOG_POSTS.find((p) => p.slug === slug);
    if (!post) throw new Error("مقاله یافت نشد.");
    return post;
  },

  async getProductsByIds(ids: number[]): Promise<ProductSummary[]> {
    await sleep(env.MOCK_LATENCY_MS);
    return PRODUCTS.filter((p) => ids.includes(p.id) && p.is_active).map(toSummary);
  },

  async submitCheckout(payload: CheckoutPayload): Promise<CheckoutResponse> {
    await sleep(env.MOCK_LATENCY_MS);
    const estimated =
      payload.mode === "purchase"
        ? payload.items.reduce((sum, it) => {
            const p = PRODUCTS.find((x) => x.id === it.product_id);
            return sum + Number(p?.base_price ?? 0) * it.quantity;
          }, 0)
        : null;
    const id = Math.floor(100000 + Math.random() * 900000);
    const tracking = `KZ-${id}`;
    const isPurchase = payload.mode === "purchase";
    const status = isPurchase ? ("pending_payment" as const) : ("inquiry_review" as const);
    const statusLabel = ORDER_STATUS_LABELS[status];

    mockOrders.set(id, {
      order_id: id,
      tracking_code: tracking,
      mode: payload.mode,
      status,
      status_label: statusLabel,
      estimated_total: estimated != null ? String(estimated) : null,
      created_at: new Date().toISOString(),
      customer_phone: payload.customer.phone,
      customer_name: payload.customer.full_name,
      items: payload.items.map((it) => {
        const p = PRODUCTS.find((x) => x.id === it.product_id);
        return {
          product_id: it.product_id,
          quantity: it.quantity,
          unit_price: p?.base_price ?? null,
        };
      }),
    });
    persistOrders();

    if (payload.mode === "purchase" && !payload.customer.is_guest) {
      mockSession.phone = payload.customer.phone;
      mockSession.full_name = payload.customer.full_name;
    }

    return {
      order_id: id,
      tracking_code: tracking,
      mode: payload.mode,
      status,
      status_label: statusLabel,
      estimated_total: estimated != null ? String(estimated) : null,
      created_at: new Date().toISOString(),
    };
  },

  async initPayment(payload: PaymentInitPayload): Promise<PaymentInitResponse> {
    await sleep(env.MOCK_LATENCY_MS);
    const order = mockOrders.get(payload.order_id);
    if (!order) throw new Error("سفارش یافت نشد.");
    if (order.status !== "pending_payment") throw new Error("این سفارش قابل پرداخت نیست.");

    const authority = `MOCK-${payload.order_id}-${Date.now()}`;
    mockPayments.set(authority, { order_id: payload.order_id, authority });
    persistPayments();

    const base =
      typeof window !== "undefined"
        ? window.location.origin
        : "http://localhost:3000";

    return {
      authority,
      payment_url: `${base}/checkout/payment/callback?Authority=${authority}&Status=OK`,
    };
  },

  async verifyPayment(payload: PaymentVerifyPayload): Promise<PaymentVerifyResponse> {
    await sleep(env.MOCK_LATENCY_MS);

    const paymentEntry = mockPayments.get(payload.authority);
    const orderId = payload.order_id ?? paymentEntry?.order_id;

    if (payload.status && payload.status.toUpperCase() !== "OK") {
      return {
        success: false,
        order_id: orderId ?? 0,
        tracking_code: "",
        status: "pending_payment",
        status_label: ORDER_STATUS_LABELS.pending_payment,
        ref_id: null,
        message: "پرداخت توسط کاربر لغو شد یا ناموفق بود.",
      };
    }

    if (!paymentEntry || (payload.order_id != null && paymentEntry.order_id !== payload.order_id)) {
      return {
        success: false,
        order_id: orderId ?? 0,
        tracking_code: "",
        status: "pending_payment",
        status_label: ORDER_STATUS_LABELS.pending_payment,
        ref_id: null,
        message: "تراکنش نامعتبر است.",
      };
    }

    const order = mockOrders.get(paymentEntry.order_id);
    if (!order) {
      return {
        success: false,
        order_id: paymentEntry.order_id,
        tracking_code: "",
        status: "pending_payment",
        status_label: ORDER_STATUS_LABELS.pending_payment,
        ref_id: null,
        message: "سفارش مرتبط یافت نشد.",
      };
    }

    order.status = "paid";
    order.status_label = ORDER_STATUS_LABELS.paid;
    persistOrders();

    return {
      success: true,
      order_id: order.order_id,
      tracking_code: order.tracking_code,
      status: "paid",
      status_label: ORDER_STATUS_LABELS.paid,
      ref_id: `MOCKREF-${payload.authority.slice(-8)}`,
      message: "پرداخت با موفقیت انجام شد.",
    };
  },

  async listMyOrders(params: { skip?: number; limit?: number } = {}): Promise<OrderListResponse> {
    await sleep(env.MOCK_LATENCY_MS);
    const token = typeof window !== "undefined" ? localStorage.getItem("karzar.storefront.token") : null;
    if (!token) {
      return { data: [], meta: { total_count: 0, skip: 0, limit: 20, has_next: false, has_prev: false } };
    }

    const all = [...mockOrders.values()]
      .filter((o) => o.customer_phone === mockSession.phone)
      .sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      );
    const skip = params.skip ?? 0;
    const limit = params.limit ?? 20;
    const page = all.slice(skip, skip + limit);

    return {
      data: page.map((o) => ({
        id: o.order_id,
        tracking_code: o.tracking_code,
        status: o.status,
        status_label: o.status_label,
        mode: o.mode,
        estimated_total: o.estimated_total,
        created_at: o.created_at,
      })),
      meta: {
        total_count: all.length,
        skip,
        limit,
        has_next: skip + limit < all.length,
        has_prev: skip > 0,
      },
    };
  },

  async trackOrder(trackingCode: string): Promise<OrderTracking> {
    await sleep(env.MOCK_LATENCY_MS);
    const order = [...mockOrders.values()].find((o) => o.tracking_code === trackingCode);
    if (!order) throw new Error("سفارش با این کد پیگیری یافت نشد.");

    const timeline = buildOrderTimeline({
      status: order.status,
      mode: order.mode,
      created_at: order.created_at,
      postal_tracking_code: order.postal_tracking_code,
      delivery_eta: order.delivery_eta,
    });

    return {
      tracking_code: order.tracking_code,
      status: order.status,
      status_label: order.status_label,
      mode: order.mode,
      estimated_total: order.estimated_total,
      created_at: order.created_at,
      postal_tracking_code: order.postal_tracking_code ?? null,
      delivery_eta: order.delivery_eta ?? null,
      items: order.items.map((item) => ({
        product_id: item.product_id,
        quantity: item.quantity,
        unit_price: item.unit_price,
      })),
      timeline,
      timeline_estimated: true,
    };
  },

  async getSpecLabels(): Promise<Record<string, string>> {
    await sleep(env.MOCK_LATENCY_MS);
    return {
      grade: "گرید",
      coating: "پوشش",
      geometry: "ژئومتری",
      insert_shape: "شکل اینسرت",
      corner_radius_mm: "شعاع گوشه (mm)",
      waterproof: "ضدآب (IP)",
      material: "جنس",
      standard: "استاندارد",
      range: "بازه اندازه‌گیری",
      accuracy: "دقت",
      resolution: "رزولوشن",
      battery_type: "نوع باتری",
      diameter_mm: "قطر (mm)",
      flutes: "تعداد تیغه",
      helix_angle: "زاویه مارپیچ",
      length_of_cut_mm: "طول برش (mm)",
      point_angle: "زاویه نوک",
      flute_length_mm: "طول شیار (mm)",
      data_output: "خروجی داده",
      auto_power_off: "خاموش شدن خودکار",
      has_buttons: "دارای دکمه",
      buttons_list: "دکمه‌ها",
      is_original: "اورجینال",
      has_certification: "دارای گواهی",
      coolant_through: "آبسردکن داخلی",
    };
  },

  async getSpecFilterOptions(categoryId: number): Promise<SpecFilterOptions> {
    await sleep(env.MOCK_LATENCY_MS);
    const category = flatById.get(categoryId);
    const ids = new Set(collectDescendantIds(CATEGORIES, categoryId));
    const inCategory = PRODUCTS.filter(
      (p) => p.category_id != null && ids.has(p.category_id) && p.is_active,
    );
    const valuesByKey: Record<string, Set<string>> = {};
    for (const p of inCategory) {
      for (const row of p.specifications?.technical_specs ?? []) {
        if (!valuesByKey[row.key]) valuesByKey[row.key] = new Set();
        valuesByKey[row.key].add(row.value);
      }
    }
    return {
      category_id: categoryId,
      category_name: category?.name ?? "دسته‌بندی",
      technical_specs: Object.fromEntries(
        Object.entries(valuesByKey).map(([k, v]) => [k, [...v]]),
      ),
    };
  },

  async getMe(): Promise<MeResponse> {
    await sleep(env.MOCK_LATENCY_MS);
    return {
      id: mockSession.id,
      phone: mockSession.phone,
      full_name: mockSession.full_name,
    };
  },

  async submitContact(payload: ContactValues): Promise<{ ok: true; ticket: string }> {
    await sleep(env.MOCK_LATENCY_MS);
    void payload;
    const ticketNum = Math.floor(10000 + Math.random() * 90000);
    const ticket = `TK-${ticketNum}`.replace(/\d/g, (d) => "۰۱۲۳۴۵۶۷۸۹"[Number(d)]);
    return { ok: true, ticket };
  },

  async listHeroSlides(): Promise<HeroSlide[]> {
    await sleep(env.MOCK_LATENCY_MS);
    return HERO_SLIDES;
  },

  async requestOtp(payload: OtpRequestPayload): Promise<OtpRequestResponse> {
    await sleep(env.MOCK_LATENCY_MS);
    return { phone: payload.phone, expires_in: 120, dev_code: "11111" };
  },

  async verifyOtp(payload: OtpVerifyPayload): Promise<OtpVerifyResponse> {
    await sleep(env.MOCK_LATENCY_MS);
    if (payload.code !== "11111") {
      throw new Error("کد وارد شده صحیح نیست.");
    }
    mockSession.phone = payload.phone;
    mockSession.full_name = mockSession.full_name ?? null;
    if (typeof window !== "undefined") {
      localStorage.setItem(
        "karzar.storefront.customer",
        JSON.stringify({ phone: payload.phone, full_name: mockSession.full_name }),
      );
    }
    return {
      access_token: "mock-storefront-token",
      refresh_token: "mock-storefront-refresh",
      token_type: "bearer",
      expires_in: 3600,
      customer: { id: mockSession.id, phone: payload.phone, full_name: mockSession.full_name },
    };
  },
};
