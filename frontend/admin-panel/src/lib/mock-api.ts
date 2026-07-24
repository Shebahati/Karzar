/**
 * In-memory mock API.
 *
 * Mirrors the FastAPI contract (response envelopes, error codes, step-up flow)
 * so the admin panel behaves identically once `NEXT_PUBLIC_USE_MOCK=false`
 * routes the same calls to the live backend. All data lives in module scope
 * and persists for the lifetime of the browser tab.
 */
import { env } from "@/config/env";
import { ApiError } from "@/lib/api-client";
import { getAdminSettings } from "@/lib/admin-settings";
import { timelineDescription } from "@/features/orders/order-workflow";
import { flattenCategoryTree } from "@/features/catalog/utils/category-tree";
import type { StepUpTokenResponse } from "@/types/auth";
import type { Token } from "@/types/auth";
import type { Brand, BrandDeleteResult, CategoryCreatePayload, CategoryDeleteResult, CategoryFlat, CategoryTreeNode, CategoryUpdatePayload, BrandCreatePayload, BrandUpdatePayload } from "@/types/category";
import type {
  Article,
  ArticleCreatePayload,
  ArticleListParams,
  ArticleListResponse,
  ArticleUpdatePayload,
  ContactSubmission,
  ContactSubmissionListParams,
  ContactSubmissionListResponse,
  HeroSlide,
  HeroSlideCreatePayload,
  HeroSlideListParams,
  HeroSlideListResponse,
  HeroSlideUpdatePayload,
  ProductComment,
  ProductCommentListParams,
  ProductCommentListResponse,
} from "@/types/cms";
import type { CustomerDetail, CustomerListParams, CustomerListResponse, CustomerUpdatePayload } from "@/types/customer";
import type {
  IssueQuotePayload,
  OrderDetail,
  OrderListParams,
  OrderListResponse,
  OrderStatus,
  OrderStatusUpdatePayload,
  OrderTimelineEvent,
} from "@/types/order";
import type { CategorySpecTemplate } from "@/types/spec-template";
import type {
  BulkStockAdjustItem,
  BulkStockAdjustResponse,
  ProductChangeLogEntry,
  ProductChangeLogListResponse,
  ProductCreatePayload,
  ProductDetail,
  ProductImageUploadResponse,
  ProductListParams,
  ProductListResponse,
  ProductStatisticsResponse,
  ProductStockAdjustPayload,
  ProductStockInfo,
  ProductSummary,
  ProductUpdatePayload,
  Specifications,
  StockUnit,
} from "@/types/product";
import type { AuditLogEntry, AuditLogListParams, AuditLogListResponse } from "@/types/audit";

import { MOCK_ADMIN_CREDENTIALS } from "@/lib/mock-credentials";

const STATIC_ADMIN_PIN = "84729101";

function delay<T>(value: T): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), env.MOCK_LATENCY_MS));
}

function nowIso(): string {
  return new Date().toISOString();
}

/* -------------------------------------------------------------------------- */
/*  Seed data                                                                 */
/* -------------------------------------------------------------------------- */

const categories: CategoryTreeNode[] = [
  {
    id: 1,
    name: "ابزار تراشکاری",
    parent_id: null,
    subcategories: [
      { id: 11, name: "الماس تراشکاری (اینسرت)", parent_id: 1, subcategories: [] },
      { id: 12, name: "هلدر و نگهدارنده", parent_id: 1, subcategories: [] },
      { id: 13, name: "بار تراش (Boring Bar)", parent_id: 1, subcategories: [] },
    ],
  },
  {
    id: 2,
    name: "ابزار فرزکاری",
    parent_id: null,
    subcategories: [
      { id: 21, name: "تیغه فرز انگشتی", parent_id: 2, subcategories: [] },
      { id: 22, name: "کله گاوی", parent_id: 2, subcategories: [] },
    ],
  },
  {
    id: 3,
    name: "ابزار سوراخکاری",
    parent_id: null,
    subcategories: [
      { id: 31, name: "مته HSS", parent_id: 3, subcategories: [] },
      { id: 32, name: "مته کارباید", parent_id: 3, subcategories: [] },
    ],
  },
  {
    id: 4,
    name: "ابزار اندازه‌گیری",
    parent_id: null,
    subcategories: [
      {
        id: 41,
        name: "کولیس",
        parent_id: 4,
        subcategories: [
          { id: 411, name: "کولیس دیجیتال ۰-۱۵۰mm", parent_id: 41, subcategories: [] },
        ],
      },
      { id: 42, name: "میکرومتر", parent_id: 4, subcategories: [] },
    ],
  },
];

(function expandAdminCategoryTree() {
  let nextId = 500;
  const l1Names = [
    "ابزار بادی و پنوماتیک",
    "جوش و برش",
    "ایمنی و حفاظت فردی",
    "لوازم جانبی و مصرفی",
    "ابزار باغبانی",
    "رفع‌سازی و نگهداری",
    "ابزار دقیق‌سازی",
    "حمل‌ونقل و انبارداری",
  ];
  const l2Suffixes = ["صنعتی", "حرفه‌ای", "نیمه‌صنعتی", "سبک", "سنگین", "تخصصی"];
  const l3Suffixes = ["سری استاندارد", "سری پیشرفته", "سری اقتصادی", "سری حرفه‌ای"];

  for (const l1Name of l1Names) {
    if (categories.some((c) => c.name === l1Name)) continue;
    const l1Id = nextId++;
    const l1Node: CategoryTreeNode = {
      id: l1Id,
      name: l1Name,
      parent_id: null,
      subcategories: [],
    };
    for (const l2Suffix of l2Suffixes) {
      const l2Id = nextId++;
      const l2Node: CategoryTreeNode = {
        id: l2Id,
        name: `${l1Name} ${l2Suffix}`,
        parent_id: l1Id,
        subcategories: [],
      };
      for (const l3Suffix of l3Suffixes) {
        l2Node.subcategories.push({
          id: nextId++,
          name: `${l2Suffix} — ${l3Suffix}`,
          parent_id: l2Id,
          subcategories: [],
        });
      }
      l1Node.subcategories.push(l2Node);
    }
    categories.push(l1Node);
  }
})();

const brands: Brand[] = [
  { id: 1, name: "سندویک کرومانت", country: "سوئد" },
  { id: 2, name: "ایسکار", country: "اسرائیل" },
  { id: 3, name: "میتوتویو", country: "ژاپن" },
  { id: 4, name: "والتر", country: "آلمان" },
  { id: 5, name: "کنمتال", country: "آمریکا" },
];

interface MockProduct extends Omit<ProductDetail, "category" | "brand"> {
  category_id: number;
  brand_id: number | null;
  is_deleted?: boolean;
}

function findCategory(id: number): { id: number; name: string } | null {
  function walk(nodes: CategoryTreeNode[]): { id: number; name: string } | null {
    for (const node of nodes) {
      if (node.id === id) return { id: node.id, name: node.name };
      const found = walk(node.subcategories);
      if (found) return found;
    }
    return null;
  }
  return walk(categories);
}

function findBrand(id: number | null): { id: number; name: string; country?: string | null } | null {
  if (id === null) return null;
  const brand = brands.find((b) => b.id === id);
  return brand ? { id: brand.id, name: brand.name, country: brand.country ?? null } : null;
}

function statusLabel(status: OrderStatus): string {
  const labels: Record<OrderStatus, string> = {
    pending_payment: "در انتظار پرداخت",
    paid: "پرداخت شده",
    processing: "در حال پردازش",
    shipped: "ارسال شده",
    delivered: "تحویل شده",
    cancelled: "لغو شده",
    inquiry_review: "در حال بررسی استعلام",
    inquiry_quoted: "پیش‌فاکتور صادر شد",
    inquiry_closed: "پرونده بسته شد",
  };
  return labels[status];
}

function appendTimeline(order: OrderDetail, status: OrderStatus, description?: string) {
  const event: OrderTimelineEvent = {
    status,
    status_label: statusLabel(status),
    occurred_at: nowIso(),
    description: description ?? timelineDescription(status, order.mode),
    actor: "admin",
  };
  order.timeline = [event, ...(order.timeline ?? [])];
}

let nextInvoiceSeq = 140401;

const mockOrders: OrderDetail[] = [
  {
    id: 1001,
    tracking_code: "KZ-100001",
    status: "paid",
    status_label: "پرداخت شده",
    mode: "purchase",
    customer_name: "رضا محمدی",
    customer_phone: "09121234567",
    estimated_total: "1850000.00",
    created_at: nowIso(),
    note: null,
    shipping_address: "تهران، خیابان ولیعصر",
    payment_status: "paid",
    postal_tracking_code: "1234567890123456",
    delivery_eta: null,
    timeline: [
      {
        status: "paid",
        status_label: "پرداخت شده",
        occurred_at: nowIso(),
        description: "پرداخت آنلاین تأیید شد",
        actor: "system",
      },
    ],
    invoice: null,
    items: [
      {
        product_id: 1,
        product_name: "الماس تراشکاری CNMG 120408",
        sku: "CNMG-120408",
        quantity: 2,
        unit_price: "925000.00",
        line_total: "1850000.00",
      },
    ],
  },
  {
    id: 1002,
    tracking_code: "KZ-200001",
    status: "inquiry_review",
    status_label: "در حال بررسی استعلام",
    mode: "inquiry",
    customer_name: "علی رضایی",
    customer_phone: "09131112233",
    estimated_total: null,
    created_at: nowIso(),
    note: "نیاز به پیش‌فاکتور رسمی",
    shipping_address: null,
    payment_status: null,
    timeline: [],
    invoice: null,
    items: [
      {
        product_id: 3,
        product_name: "تیغ فرز انگشتی کارباید قطر ۱۰ چهار پر",
        sku: "EMILL-D10-Z4",
        quantity: 5,
        unit_price: null,
        line_total: null,
      },
    ],
  },
  {
    id: 1003,
    tracking_code: "KZ-200002",
    status: "inquiry_quoted",
    status_label: "پیش‌فاکتور صادر شد",
    mode: "inquiry",
    customer_name: "شرکت صنعت‌ساز",
    customer_phone: "02188776655",
    estimated_total: "12500000.00",
    created_at: nowIso(),
    note: "استعلام B2B",
    shipping_address: "تهران، شهرک صنعتی",
    payment_status: null,
    timeline: [
      {
        status: "inquiry_quoted",
        status_label: "پیش‌فاکتور صادر شد",
        occurred_at: nowIso(),
        description: "پیش‌فاکتور برای مشتری صادر شد",
        actor: "admin",
      },
    ],
    invoice: {
      invoice_number: `INV-${nextInvoiceSeq++}`,
      issued_at: nowIso(),
      valid_until: null,
      total: "12500000.00",
      note: "استعلام B2B",
    },
    items: [
      {
        product_id: 5,
        product_name: "کولیس دیجیتال ۱۵۰ میلی‌متر ضدآب",
        sku: "CALIPER-150-DIG",
        quantity: 2,
        unit_price: "5600000.00",
        line_total: "11200000.00",
      },
    ],
  },
];

const mockCustomers: CustomerDetail[] = [
  {
    id: 1,
    phone: "09121234567",
    full_name: "رضا محمدی",
    is_active: true,
    order_count: 3,
    created_at: nowIso(),
    email: null,
    note: "مشتری وفادار — ترجیح تحویل صبح",
    category: "سازمانی",
    tags: ["VIP", "تهران"],
  },
  {
    id: 2,
    phone: "09129876543",
    full_name: "سارا احمدی",
    is_active: true,
    order_count: 1,
    created_at: nowIso(),
    email: "sara@example.com",
    note: "مشتری سازمانی",
    category: "عمده",
    tags: ["B2B", "اصفهان"],
  },
  {
    id: 3,
    phone: "09131112233",
    full_name: "علی رضایی",
    is_active: true,
    order_count: 1,
    created_at: nowIso(),
    email: null,
    note: null,
    category: "خرده",
    tags: ["استعلام‌گر"],
  },
];

/* -------------------------------------------------------------------------- */
/*  CMS seed data                                                             */
/* -------------------------------------------------------------------------- */

const articles: Article[] = [
  {
    id: 1,
    slug: "raznamaye-entekhab-almas-tarashkari",
    title: "راهنمای انتخاب الماس تراشکاری مناسب",
    excerpt: "با در نظر گرفتن جنس قطعه کار، سرعت برشی و نوع عملیات، الماس مناسب را انتخاب کنید.",
    cover_image: "https://picsum.photos/seed/karzar-article-1/960/540",
    published_at: nowIso(),
    reading_minutes: 6,
    author: "تیم فنی کارزار",
    tags: ["تراشکاری", "الماس", "راهنمای خرید"],
    related_product_ids: [1, 2],
    blocks: [
      {
        type: "paragraph",
        text: "انتخاب الماس تراشکاری مناسب یکی از مهم‌ترین عوامل در افزایش عمر ابزار و کیفیت سطح قطعه است.",
      },
      { type: "heading", text: "عوامل مهم در انتخاب" },
      {
        type: "list",
        items: [
          "جنس و سختی قطعه کار",
          "سرعت برشی و نرخ پیشروی",
          "نوع پوشش (CVD یا PVD)",
          "شعاع نوک الماس",
        ],
      },
      { type: "quote", text: "انتخاب درست الماس، هزینه تولید را تا ۲۰٪ کاهش می‌دهد." },
    ],
    is_published: true,
    created_at: nowIso(),
    updated_at: nowIso(),
  },
  {
    id: 2,
    slug: "negahdari-abzar-frezkari",
    title: "نکات نگهداری تیغه‌های فرز انگشتی",
    excerpt: "با رعایت چند نکته ساده، عمر مفید تیغه‌های فرز انگشتی خود را چند برابر کنید.",
    cover_image: "https://picsum.photos/seed/karzar-article-2/960/540",
    published_at: nowIso(),
    reading_minutes: 4,
    author: "تیم فنی کارزار",
    tags: ["فرزکاری", "نگهداری ابزار"],
    related_product_ids: [3],
    blocks: [
      { type: "paragraph", text: "نگهداری صحیح ابزار فرز، مستقیماً روی کیفیت سطح و دقت ابعادی اثر می‌گذارد." },
      {
        type: "list",
        items: ["تمیزکاری بعد از هر استفاده", "استفاده از مایع خنک‌کننده مناسب", "بازرسی دوره‌ای لبه برش"],
      },
    ],
    is_published: true,
    created_at: nowIso(),
    updated_at: nowIso(),
  },
  {
    id: 3,
    slug: "moghayese-koolis-dijital-analog",
    title: "مقایسه کولیس دیجیتال و آنالوگ",
    excerpt: "کدام کولیس برای کارگاه شما مناسب‌تر است؟ بررسی مزایا و معایب هر دو نوع.",
    cover_image: "https://picsum.photos/seed/karzar-article-3/960/540",
    published_at: nowIso(),
    reading_minutes: 5,
    author: "نویسنده مهمان",
    tags: ["ابزار اندازه‌گیری"],
    related_product_ids: [5],
    blocks: [
      { type: "paragraph", text: "این مقاله هنوز در مرحله پیش‌نویس است و پیش از انتشار نهایی بازبینی می‌شود." },
    ],
    is_published: false,
    created_at: nowIso(),
    updated_at: nowIso(),
  },
];
let nextArticleId = articles.length + 1;

const heroSlides: HeroSlide[] = [
  {
    id: 1,
    title: "فروش ویژه ابزار تراشکاری",
    subtitle: "تا ۲۰٪ تخفیف روی الماس‌های تراشکاری منتخب",
    cta_label: "مشاهده محصولات",
    cta_href: "/products?category=11",
    image: "https://picsum.photos/seed/karzar-hero-1/1600/700",
    accent: "#C22026",
    sort_order: 1,
    is_active: true,
  },
  {
    id: 2,
    title: "ابزار اندازه‌گیری دقیق",
    subtitle: "کولیس و میکرومتر دیجیتال با گارانتی اصالت",
    cta_label: "خرید کنید",
    cta_href: "/products?category=4",
    image: "https://picsum.photos/seed/karzar-hero-2/1600/700",
    accent: "#1F5FBF",
    sort_order: 2,
    is_active: true,
  },
  {
    id: 3,
    title: "ارسال رایگان سفارش‌های بالای ۵ میلیون تومان",
    subtitle: null,
    cta_label: null,
    cta_href: null,
    image: "https://picsum.photos/seed/karzar-hero-3/1600/700",
    accent: "#1E8E5A",
    sort_order: 3,
    is_active: false,
  },
];
let nextHeroSlideId = heroSlides.length + 1;

const productComments: ProductComment[] = [
  {
    id: 1,
    product_id: 1,
    author_name: "رضا محمدی",
    rating: 5,
    body: "کیفیت الماس عالی بود، دقیقاً مطابق مشخصات سایت.",
    created_at: nowIso(),
    is_verified_buyer: true,
  },
  {
    id: 2,
    product_id: 1,
    author_name: "کاربر مهمان",
    rating: 3,
    body: "بسته‌بندی می‌توانست بهتر باشد اما خود محصول خوب است.",
    created_at: nowIso(),
    is_verified_buyer: false,
  },
  {
    id: 3,
    product_id: 3,
    author_name: "علی رضایی",
    rating: 4,
    body: "برای فرزکاری آلومینیوم عملکرد خوبی داشت.",
    created_at: nowIso(),
    is_verified_buyer: true,
  },
  {
    id: 4,
    product_id: 5,
    author_name: "سارا احمدی",
    rating: 5,
    body: "دقت اندازه‌گیری کولیس فوق‌العاده است، پیشنهاد می‌کنم.",
    created_at: nowIso(),
    is_verified_buyer: true,
  },
  {
    id: 5,
    product_id: 6,
    author_name: "شرکت صنعت‌ساز",
    rating: 2,
    body: "زمان تحویل کمی طول کشید.",
    created_at: nowIso(),
    is_verified_buyer: false,
  },
];

const contactSubmissions: ContactSubmission[] = [
  {
    id: 1,
    ticket_code: "TCK-10021",
    full_name: "محمد کریمی",
    phone: "09121230012",
    subject: "استعلام موجودی محصول",
    message: "سلام، آیا مته HSS قطر ۸.۵ در انبار موجود است؟",
    created_at: nowIso(),
  },
  {
    id: 2,
    ticket_code: "TCK-10022",
    full_name: "شرکت فولاد پارس",
    phone: "02188990011",
    subject: "درخواست همکاری B2B",
    message: "برای خریدهای عمده، تخفیف ویژه‌ای در نظر دارید؟",
    created_at: nowIso(),
  },
  {
    id: 3,
    ticket_code: "TCK-10023",
    full_name: "نگار حسینی",
    phone: "09351234567",
    subject: "مشکل در ارسال سفارش",
    message: "سفارش من با کد پیگیری KZ-100001 هنوز به دستم نرسیده.",
    created_at: nowIso(),
  },
  {
    id: 4,
    ticket_code: "TCK-10024",
    full_name: "امیر توکلی",
    phone: "09190001122",
    subject: "راهنمایی فنی",
    message: "کدام الماس برای برش استیل ضدزنگ مناسب‌تر است؟",
    created_at: nowIso(),
  },
];

function buildSeedProduct(
  partial: Pick<MockProduct, "id" | "sku" | "name" | "category_id" | "brand_id" | "base_price" | "stock_quantity" | "stock_unit"> &
    Partial<Omit<MockProduct, "specifications">> & {
      specifications?: Record<string, unknown>;
    },
): MockProduct {
  const seedImages = (productId: number, count = 3) => {
    const images = Array.from({ length: count }, (_, i) => ({
      id: productId * 100 + i,
      url: `https://picsum.photos/seed/karzar-admin-${productId}-${i}/800/800`,
      is_primary: i === 0,
    }));
    return { thumbnail: images[0].url, images };
  };

  const seeded = partial.images?.length ? {} : seedImages(partial.id);

  return {
    description: null,
    original_price: null,
    discount_percent: null,
    warranty_text: "۱۸ ماه گارانتی شرکتی",
    weight_grams: "250.00",
    is_original: true,
    tax_percent: "9.00",
    is_active: true,
    pdf_catalog_url: null,
    thumbnail: null,
    images: [],
    low_stock: Number(partial.stock_quantity) < 5,
    availability: Number(partial.stock_quantity) > 0,
    stock_status: Number(partial.stock_quantity) > 0 ? "in_stock" : "out_of_stock",
    created_at: nowIso(),
    updated_at: nowIso(),
    ...partial,
    ...seeded,
    specifications: (partial.specifications ?? {}) as Specifications,
  };
}

const products: MockProduct[] = [
  buildSeedProduct({
    id: 1,
    sku: "CNMG-120408",
    name: "الماس تراشکاری CNMG 120408 روکش CVD",
    category_id: 11,
    brand_id: 1,
    base_price: "1850000.00",
    stock_quantity: "120.00",
    stock_unit: "piece",
    specifications: {
      grade: "GC4325",
      coating: "CVD",
      geometry: "PM",
      insert_shape: "C (80°)",
      corner_radius_mm: 0.8,
    },
  }),
  buildSeedProduct({
    id: 2,
    sku: "DCMT-11T304",
    name: "الماس تراشکاری DCMT 11T304 پرداختکاری",
    category_id: 11,
    brand_id: 2,
    base_price: "1320000.00",
    stock_quantity: "3.00",
    stock_unit: "piece",
    specifications: {
      grade: "IC907",
      coating: "PVD",
      insert_shape: "D (55°)",
      corner_radius_mm: 0.4,
    },
  }),
  buildSeedProduct({
    id: 3,
    sku: "EMILL-D10-Z4",
    name: "تیغ فرز انگشتی کارباید قطر ۱۰ چهار پر",
    category_id: 21,
    brand_id: 4,
    base_price: "4200000.00",
    stock_quantity: "42.00",
    stock_unit: "piece",
    specifications: {
      diameter_mm: 10,
      flutes: 4,
      coating: "AlTiN",
      helix_angle: "45°",
      length_of_cut_mm: 22,
    },
  }),
  buildSeedProduct({
    id: 4,
    sku: "DRILL-HSS-8.5",
    name: "مته HSS کبالت‌دار قطر ۸.۵ میلی‌متر",
    category_id: 31,
    brand_id: 5,
    base_price: "320000.00",
    stock_quantity: "0.00",
    stock_unit: "piece",
    specifications: {
      diameter_mm: 8.5,
      material: "HSS-Co5",
      standard: "DIN 338",
      point_angle: "135°",
    },
  }),
  buildSeedProduct({
    id: 5,
    sku: "CALIPER-150-DIG",
    name: "کولیس دیجیتال ۱۵۰ میلی‌متر ضدآب",
    category_id: 41,
    brand_id: 3,
    base_price: "5600000.00",
    stock_quantity: "18.00",
    stock_unit: "piece",
    specifications: {
      range: "0-150mm",
      resolution: "0.01mm",
      accuracy: "±0.02mm",
      waterproof: true,
      data_output: true,
    },
  }),
  buildSeedProduct({
    id: 6,
    sku: "BORBAR-S16Q",
    name: "بار تراش داخل‌تراش S16Q-SCLCR09",
    category_id: 13,
    brand_id: 1,
    base_price: "8900000.00",
    stock_quantity: "7.00",
    stock_unit: "piece",
    specifications: {
      shank_diameter_mm: 16,
      min_bore_mm: 20,
      insert: "CCMT 09",
      coolant_through: true,
    },
  }),
];

let nextProductId = products.length + 1;

let nextAuditLogId = 1;
const auditLogs: AuditLogEntry[] = [];

function recordAuditLog(
  action: string,
  entityType: string,
  entityId: string,
  details?: Record<string, unknown> | null,
) {
  auditLogs.unshift({
    id: nextAuditLogId++,
    actor_user_id: 1,
    action,
    entity_type: entityType,
    entity_id: entityId,
    details: details ?? null,
    created_at: nowIso(),
  });
}

const productChangeLogs: ProductChangeLogEntry[] = [
  {
    id: 1,
    product_id: 1,
    field_name: "base_price",
    old_value: "1800000.00",
    new_value: "1850000.00",
    reason: "به‌روزرسانی قیمت تامین‌کننده",
    created_at: nowIso(),
  },
  {
    id: 2,
    product_id: 1,
    field_name: "stock_quantity",
    old_value: "100.00",
    new_value: "120.00",
    reason: "ورود محموله جدید",
    created_at: nowIso(),
  },
  {
    id: 3,
    product_id: 2,
    field_name: "base_price",
    old_value: "1250000.00",
    new_value: "1320000.00",
    reason: null,
    created_at: nowIso(),
  },
];
let nextChangeLogId = productChangeLogs.length + 1;

recordAuditLog("update", "product", "2", { field: "base_price", new_value: "1320000.00" });
recordAuditLog("soft_delete", "product", "999", { note: "نمونه ممیزی — محصول آزمایشی" });

(function expandAdminProducts() {
  const flat = flattenCategoryTree(categories);
  const leafIds = flat.filter((c) => !flat.some((x) => x.parent_id === c.id)).map((c) => c.id);
  const templates = products.slice(0, 4);
  for (let i = 0; i < leafIds.length; i++) {
    const leafId = leafIds[i];
    if (products.some((p) => p.category_id === leafId)) continue;
    const template = templates[i % templates.length];
    products.push(
      buildSeedProduct({
        id: nextProductId++,
        sku: `${template.sku}-V${leafId}`,
        name: `${template.name} — ${leafId}`,
        category_id: leafId,
        brand_id: template.brand_id,
        base_price: template.base_price,
        stock_quantity: String(10 + (i % 30)),
        stock_unit: template.stock_unit,
        specifications: template.specifications as Record<string, unknown>,
      }),
    );
  }
})();

/* -------------------------------------------------------------------------- */
/*  Presenters                                                                */
/* -------------------------------------------------------------------------- */

function toSummary(product: MockProduct): ProductSummary {
  return {
    id: product.id,
    sku: product.sku,
    name: product.name,
    thumbnail: product.thumbnail,
    base_price: product.base_price,
    original_price: product.original_price,
    discount_percent: product.discount_percent,
    stock_status: product.stock_status,
    availability: product.availability,
    is_original: product.is_original,
    category: findCategory(product.category_id),
    brand: findBrand(product.brand_id),
  };
}

function toDetail(product: MockProduct): ProductDetail {
  return {
    ...product,
    category: findCategory(product.category_id),
    brand: findBrand(product.brand_id),
  };
}

/* -------------------------------------------------------------------------- */
/*  Mock endpoints                                                            */
/* -------------------------------------------------------------------------- */

/* -------------------------------------------------------------------------- */
/*  Mock endpoints                                                            */
/* -------------------------------------------------------------------------- */

const MOCK_SPEC_TEMPLATE: CategorySpecTemplate = {
  category_id: 411,
  category_name: "کولیس دیجیتال ۰-۱۵۰mm",
  breadcrumb: ["ابزار اندازه‌گیری", "کولیس", "کولیس دیجیتال ۰-۱۵۰mm"],
  technical_specs: {
    suggested_keys: ["range", "accuracy", "resolution", "material", "standard", "battery_type"],
    value_options: {
      range: ["0-150mm", "0-200mm"],
      accuracy: ["±0.02mm", "±0.03mm"],
      resolution: ["0.01mm", "0.001mm"],
      material: ["فولاد ضدزنگ", "Stainless steel"],
      standard: ["DIN862", "ISO13385"],
      battery_type: ["CR2032"],
    },
  },
  features: [
    { key: "waterproof", label: "ضدآب (IP)", type: "boolean" },
    { key: "data_output", label: "خروجی داده", type: "boolean" },
    { key: "auto_power_off", label: "خاموش شدن خودکار", type: "boolean" },
    {
      key: "has_buttons",
      label: "دارای دکمه",
      type: "boolean",
      detail: {
        key: "buttons_list",
        label: "چه دکمه‌هایی دارد؟",
        type: "string_array",
        placeholder: "on/off",
      },
    },
  ],
  dimensions: { suggested_keys: ["L", "a", "b", "c", "d"] },
  default_values: {
    technical_specs: [
      { key: "range", value: "" },
      { key: "accuracy", value: "" },
      { key: "resolution", value: "" },
      { key: "material", value: "" },
      { key: "standard", value: "" },
      { key: "battery_type", value: "" },
    ],
    features: {
      waterproof: false,
      data_output: false,
      auto_power_off: false,
      has_buttons: false,
      buttons_list: [],
    },
    dimensions: [
      { key: "L", value: null },
      { key: "a", value: null },
      { key: "b", value: null },
      { key: "c", value: null },
      { key: "d", value: null },
    ],
  },
};

export const mockApi = {
  async listProducts(params: ProductListParams = {}): Promise<ProductListResponse> {
    const { skip = 0, limit = 20, search, category_id, brand_id, is_active, is_deleted } = params;

    let filtered = [...products];
    if (params.is_deleted) {
      filtered = filtered.filter((p) => p.is_deleted);
    } else {
      filtered = filtered.filter((p) => !p.is_deleted);
    }
    if (search) {
      const term = search.trim().toLowerCase();
      filtered = filtered.filter(
        (p) => p.name.toLowerCase().includes(term) || p.sku.toLowerCase().includes(term),
      );
    }
    if (category_id !== undefined) {
      filtered = filtered.filter((p) => p.category_id === category_id);
    }
    if (brand_id !== undefined) {
      filtered = filtered.filter((p) => p.brand_id === brand_id);
    }
    if (is_active !== undefined) {
      filtered = filtered.filter((p) => p.is_active === is_active);
    }

    const total = filtered.length;
    const page = filtered.slice(skip, skip + limit).map(toSummary);

    return delay({
      data: page,
      meta: {
        total_count: total,
        skip,
        limit,
        has_next: skip + limit < total,
        has_prev: skip > 0,
      },
    });
  },

  async getProduct(id: number): Promise<ProductDetail> {
    const product = products.find((p) => p.id === id);
    if (!product) {
      throw new ApiError({
        status: 404,
        code: "NOT_FOUND",
        message: `محصول با شناسه ${id} یافت نشد.`,
      });
    }
    return delay(toDetail(product));
  },

  async createProduct(payload: ProductCreatePayload): Promise<ProductDetail> {
    const sku = payload.sku.trim().toUpperCase();
    if (products.some((p) => p.sku === sku)) {
      throw new ApiError({
        status: 409,
        code: "CONFLICT",
        message: `محصولی با کد «${sku}» از قبل ثبت شده است.`,
        fieldErrors: { sku: "این کد محصول تکراری است." },
      });
    }

    const created: MockProduct = {
      id: nextProductId++,
      sku,
      name: payload.name.trim(),
      description: payload.description ?? null,
      category_id: payload.category_id,
      brand_id: payload.brand_id ?? null,
      base_price: payload.base_price != null ? payload.base_price.toFixed(2) : null,
      original_price: payload.original_price != null ? payload.original_price.toFixed(2) : null,
      discount_percent: null,
      stock_quantity: payload.stock_quantity.toFixed(2),
      stock_unit: payload.stock_unit as StockUnit,
      stock_status: payload.stock_quantity > 0 ? "in_stock" : "out_of_stock",
      low_stock: payload.stock_quantity < 5,
      availability: payload.stock_quantity > 0,
      warranty_text: payload.warranty_text ?? null,
      weight_grams: payload.weight_grams != null ? payload.weight_grams.toFixed(2) : null,
      is_original: payload.is_original,
      tax_percent: payload.tax_percent.toFixed(2),
      is_active: payload.is_active,
      pdf_catalog_url: payload.pdf_catalog_url ?? null,
      thumbnail: null,
      images: [],
      specifications: payload.specifications,
      created_at: nowIso(),
      updated_at: nowIso(),
    };

    products.unshift(created);
    return delay(toDetail(created));
  },

  async updateProduct(id: number, payload: ProductUpdatePayload): Promise<ProductDetail> {
    const index = products.findIndex((p) => p.id === id);
    if (index === -1) {
      throw new ApiError({ status: 404, code: "NOT_FOUND", message: "Product not found" });
    }
    const current = products[index];
    if (payload.sku) current.sku = payload.sku.trim().toUpperCase();
    if (payload.name) current.name = payload.name.trim();
    if (payload.category_id) current.category_id = payload.category_id;
    if (payload.brand_id !== undefined) current.brand_id = payload.brand_id;
    if (payload.specifications) current.specifications = payload.specifications;
    current.updated_at = nowIso();
    return delay(toDetail(current));
  },

  async deleteProduct(id: number, stepUpToken: string | null): Promise<void> {
    if (!stepUpToken) {
      throw new ApiError({
        status: 403,
        code: "STEP_UP_REQUIRED",
        message: "این عملیات نیازمند تأیید هویت مرحله‌دوم (PIN) است.",
      });
    }
    const product = products.find((p) => p.id === id);
    if (!product) {
      throw new ApiError({
        status: 404,
        code: "NOT_FOUND",
        message: `محصول با شناسه ${id} یافت نشد.`,
      });
    }
    product.is_deleted = true;
    product.is_active = false;
    product.updated_at = nowIso();
    recordAuditLog("soft_delete", "product", String(id));
    return delay(undefined);
  },

  async listCategories(): Promise<CategoryTreeNode[]> {
    return delay(categories);
  },

  async listFlatCategories(): Promise<CategoryFlat[]> {
    return delay(flattenCategoryTree(categories));
  },

  async getCategorySpecTemplate(categoryId: number): Promise<CategorySpecTemplate> {
    const flat = flattenCategoryTree(categories);
    const category = flat.find((row) => row.id === categoryId);
    if (!category) {
      throw new ApiError({
        status: 404,
        code: "NOT_FOUND",
        message: `Category with ID '${categoryId}' not found`,
      });
    }
    if (!category.is_selectable) {
      throw new ApiError({
        status: 400,
        code: "BAD_REQUEST",
        message: "Spec templates are only available for layer-3 leaf categories",
      });
    }
    return delay({
      ...MOCK_SPEC_TEMPLATE,
      category_id: category.id,
      category_name: category.name,
      breadcrumb: category.breadcrumb,
    });
  },

  async listBrands(): Promise<Brand[]> {
    return delay(brands);
  },

  async createBrand(payload: BrandCreatePayload): Promise<Brand> {
    const brand: Brand = { id: brands.length + 1, name: payload.name, country: payload.country ?? null };
    brands.push(brand);
    return delay(brand);
  },

  async updateBrand(id: number, payload: BrandUpdatePayload): Promise<Brand> {
    const brand = brands.find((b) => b.id === id);
    if (!brand) throw new ApiError({ status: 404, code: "NOT_FOUND", message: "Brand not found" });
    if (payload.name) brand.name = payload.name;
    if (payload.country !== undefined) brand.country = payload.country;
    return delay(brand);
  },

  async deleteBrand(id: number, stepUpToken: string | null): Promise<BrandDeleteResult> {
    if (!stepUpToken) {
      throw new ApiError({ status: 403, code: "STEP_UP_REQUIRED", message: "Step-up required" });
    }
    const index = brands.findIndex((b) => b.id === id);
    if (index === -1) throw new ApiError({ status: 404, code: "NOT_FOUND", message: "Brand not found" });
    const cleared = products.filter((p) => p.brand_id === id).length;
    products.forEach((p) => {
      if (p.brand_id === id) p.brand_id = null;
    });
    brands.splice(index, 1);
    return delay({ id, products_cleared: cleared });
  },

  async restoreProduct(id: number): Promise<ProductDetail> {
    const product = products.find((p) => p.id === id);
    if (!product) throw new ApiError({ status: 404, code: "NOT_FOUND", message: "Product not found" });
    product.is_deleted = false;
    product.is_active = true;
    product.updated_at = nowIso();
    return delay(toDetail(product));
  },

  async getProductBySku(sku: string): Promise<ProductDetail> {
    const product = products.find((p) => p.sku.toLowerCase() === sku.trim().toLowerCase());
    if (!product) throw new ApiError({ status: 404, code: "NOT_FOUND", message: "Product not found" });
    return delay(toDetail(product));
  },

  async getProductStock(id: number): Promise<ProductStockInfo> {
    const product = products.find((p) => p.id === id);
    if (!product) throw new ApiError({ status: 404, code: "NOT_FOUND", message: "Product not found" });
    return delay({
      product_id: id,
      sku: product.sku,
      stock_quantity: product.stock_quantity,
      stock_status: product.stock_status,
      quantity: product.stock_quantity,
      unit: product.stock_unit,
      low_stock: product.low_stock,
      availability: product.availability,
    });
  },

  async adjustProductStock(id: number, payload: ProductStockAdjustPayload): Promise<ProductStockInfo> {
    const product = products.find((p) => p.id === id);
    if (!product) throw new ApiError({ status: 404, code: "NOT_FOUND", message: "Product not found" });
    const next = Math.max(0, Number(product.stock_quantity) + payload.delta);
    product.stock_quantity = String(next);
    product.low_stock = next < 5;
    product.availability = next > 0;
    product.stock_status = next > 0 ? (next < 5 ? "low_stock" : "in_stock") : "out_of_stock";
    product.updated_at = nowIso();
    return delay({
      product_id: id,
      sku: product.sku,
      stock_quantity: product.stock_quantity,
      stock_status: product.stock_status,
      quantity: product.stock_quantity,
      unit: product.stock_unit,
      low_stock: product.low_stock,
      availability: product.availability,
    });
  },

  async getProductStatistics(): Promise<ProductStatisticsResponse> {
    const alive = products.filter((p) => !p.is_deleted);
    const active = alive.filter((p) => p.is_active);
    const totalValue = alive.reduce(
      (sum, p) => sum + Number(p.base_price ?? 0) * Number(p.stock_quantity ?? 0),
      0,
    );
    const totalQty = alive.reduce((sum, p) => sum + Number(p.stock_quantity ?? 0), 0);
    const categorySet = new Set(alive.map((p) => p.category_id));
    const brandSet = new Set(alive.map((p) => p.brand_id).filter((id): id is number => id !== null));
    return delay({
      total_products: alive.length,
      active_products: active.length,
      total_stock_value: totalValue.toFixed(2),
      total_stock_quantity: totalQty.toFixed(2),
      categories: categorySet.size,
      brands: brandSet.size,
    });
  },

  async getProductChangeLog(
    productId: number,
    params: { skip?: number; limit?: number } = {},
  ): Promise<ProductChangeLogListResponse> {
    const { skip = 0, limit = 50 } = params;
    const filtered = productChangeLogs
      .filter((row) => row.product_id === productId)
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    const total = filtered.length;
    return delay({
      data: filtered.slice(skip, skip + limit),
      meta: { total_count: total, skip, limit, has_next: skip + limit < total, has_prev: skip > 0 },
    });
  },

  async bulkStockAdjust(items: BulkStockAdjustItem[]): Promise<BulkStockAdjustResponse> {
    const updated: number[] = [];
    for (const item of items) {
      const product = products.find((p) => p.id === item.product_id);
      if (!product) continue;
      const next = Math.max(0, Number(product.stock_quantity) + item.quantity_delta);
      productChangeLogs.push({
        id: nextChangeLogId++,
        product_id: product.id,
        field_name: "stock_quantity",
        old_value: product.stock_quantity,
        new_value: String(next),
        reason: item.reason ?? null,
        created_at: nowIso(),
      });
      product.stock_quantity = String(next);
      product.low_stock = next < 5;
      product.availability = next > 0;
      product.stock_status = next > 0 ? (next < 5 ? "low_stock" : "in_stock") : "out_of_stock";
      product.updated_at = nowIso();
      updated.push(product.id);
    }
    recordAuditLog("bulk_stock_adjust", "product", updated.join(","), { count: updated.length });
    return delay({ updated_product_ids: updated });
  },

  async uploadProductImage(id: number, file: File): Promise<ProductImageUploadResponse> {
    const product = products.find((p) => p.id === id);
    if (!product) throw new ApiError({ status: 404, code: "NOT_FOUND", message: "Product not found" });
    const imageId = (product.images.at(-1)?.id ?? 0) + 1;
    const url = URL.createObjectURL(file);
    const image = { id: imageId, url, is_primary: product.images.length === 0 };
    product.images.push(image);
    if (image.is_primary) product.thumbnail = url;
    product.updated_at = nowIso();
    return delay(image);
  },

  async addProductImageByUrl(id: number, imageUrl: string, isPrimary = false): Promise<ProductDetail> {
    const product = products.find((p) => p.id === id);
    if (!product) throw new ApiError({ status: 404, code: "NOT_FOUND", message: "Product not found" });
    const imageId = (product.images.at(-1)?.id ?? 0) + 1;
    const image = { id: imageId, url: imageUrl, is_primary: isPrimary || product.images.length === 0 };
    if (image.is_primary) {
      product.images.forEach((img) => {
        img.is_primary = false;
      });
      product.thumbnail = imageUrl;
    }
    product.images.push(image);
    product.updated_at = nowIso();
    return delay(toDetail(product));
  },

  async setPrimaryProductImage(productId: number, imageId: number): Promise<ProductDetail> {
    const product = products.find((p) => p.id === productId);
    if (!product) throw new ApiError({ status: 404, code: "NOT_FOUND", message: "Product not found" });
    const target = product.images.find((img) => img.id === imageId);
    if (!target) throw new ApiError({ status: 404, code: "NOT_FOUND", message: "Image not found" });
    product.images.forEach((img) => {
      img.is_primary = img.id === imageId;
    });
    product.thumbnail = target.url;
    product.updated_at = nowIso();
    return delay(toDetail(product));
  },

  async reorderProductImages(productId: number, imageIds: number[]): Promise<ProductDetail> {
    const product = products.find((p) => p.id === productId);
    if (!product) throw new ApiError({ status: 404, code: "NOT_FOUND", message: "Product not found" });
    const byId = new Map(product.images.map((img) => [img.id, img]));
    product.images = imageIds.map((id) => byId.get(id)).filter(Boolean) as typeof product.images;
    product.updated_at = nowIso();
    return delay(toDetail(product));
  },

  async getProductsByIds(ids: number[]): Promise<ProductSummary[]> {
    return delay(
      products
        .filter((p) => ids.includes(p.id) && !p.is_deleted)
        .map((p) => toSummary(p)),
    );
  },

  async deleteProductImage(productId: number, imageId: number): Promise<void> {
    const product = products.find((p) => p.id === productId);
    if (!product) throw new ApiError({ status: 404, code: "NOT_FOUND", message: "Product not found" });
    product.images = product.images.filter((img) => img.id !== imageId);
    if (!product.images.some((img) => img.is_primary) && product.images[0]) {
      product.images[0].is_primary = true;
      product.thumbnail = product.images[0].url;
    }
    product.updated_at = nowIso();
    return delay(undefined);
  },

  async listOrders(params: OrderListParams = {}): Promise<OrderListResponse> {
    const all = [...mockOrders];
    let filtered = all;
    if (params.mode) filtered = filtered.filter((o) => o.mode === params.mode);
    if (params.customer_phone) {
      filtered = filtered.filter((o) => o.customer_phone === params.customer_phone);
    }
    if (params.status) filtered = filtered.filter((o) => o.status === params.status);
    if (params.search) {
      const q = params.search.trim().toLowerCase();
      filtered = filtered.filter(
        (o) =>
          o.tracking_code.toLowerCase().includes(q) ||
          o.customer_name.toLowerCase().includes(q) ||
          o.customer_phone.includes(q),
      );
    }
    const skip = params.skip ?? 0;
    const limit = params.limit ?? 20;
    return delay({
      data: filtered.slice(skip, skip + limit),
      meta: {
        total_count: filtered.length,
        skip,
        limit,
        has_next: skip + limit < filtered.length,
        has_prev: skip > 0,
      },
    });
  },

  async getOrder(id: number): Promise<OrderDetail> {
    const order = mockOrders.find((o) => o.id === id);
    if (!order) throw new ApiError({ status: 404, code: "NOT_FOUND", message: "Order not found" });
    return delay(order);
  },

  async updateOrderStatus(id: number, payload: OrderStatusUpdatePayload): Promise<OrderDetail> {
    const order = mockOrders.find((o) => o.id === id);
    if (!order) throw new ApiError({ status: 404, code: "NOT_FOUND", message: "Order not found" });

    if (payload.status === "shipped") {
      const tracking = payload.postal_tracking_code ?? order.postal_tracking_code;
      if (!tracking || tracking.trim().length < 10) {
        throw new ApiError({
          status: 400,
          code: "VALIDATION_ERROR",
          message: "برای ثبت ارسال، کد رهگیری پست الزامی است.",
        });
      }
      order.postal_tracking_code = tracking.trim();
    }

    order.status = payload.status;
    order.status_label = statusLabel(payload.status);
    if (payload.note !== undefined) order.note = payload.note;
    if (payload.postal_tracking_code !== undefined) {
      order.postal_tracking_code = payload.postal_tracking_code;
    }
    if (payload.delivery_eta !== undefined) order.delivery_eta = payload.delivery_eta;

    if (payload.status === "paid") order.payment_status = "paid";
    if (payload.status === "delivered") order.payment_status = "paid";

    appendTimeline(order, payload.status);
    return delay(order);
  },

  async issueQuote(id: number, payload: IssueQuotePayload): Promise<OrderDetail> {
    const order = mockOrders.find((o) => o.id === id);
    if (!order) throw new ApiError({ status: 404, code: "NOT_FOUND", message: "Order not found" });
    if (order.mode !== "inquiry") {
      throw new ApiError({ status: 400, code: "BAD_REQUEST", message: "فقط استعلام‌ها قابل پیش‌فاکتور هستند." });
    }
    if (order.status !== "inquiry_review") {
      throw new ApiError({ status: 400, code: "BAD_REQUEST", message: "این استعلام در مرحله صدور پیش‌فاکتور نیست." });
    }

    let total = 0;
    for (const line of payload.items) {
      const item = order.items.find((i) => i.product_id === line.product_id);
      if (!item) continue;
      const unit = Number(line.unit_price);
      if (Number.isNaN(unit) || unit <= 0) {
        throw new ApiError({ status: 400, code: "VALIDATION_ERROR", message: "قیمت همه اقلام باید معتبر باشد." });
      }
      item.unit_price = line.unit_price;
      item.line_total = String(unit * item.quantity);
      total += unit * item.quantity;
    }

    order.estimated_total = String(total);
    order.note = payload.note ?? order.note;
    order.status = "inquiry_quoted";
    order.status_label = statusLabel("inquiry_quoted");
    order.invoice = {
      invoice_number: `INV-${nextInvoiceSeq++}`,
      issued_at: nowIso(),
      valid_until: payload.valid_until ?? null,
      total: String(total),
      note: payload.note ?? null,
    };
    appendTimeline(order, "inquiry_quoted", "پیش‌فاکتور با قیمت‌گذاری ادمین صادر شد");
    return delay(order);
  },

  async archiveOrder(id: number, stepUpToken: string | null): Promise<void> {
    if (!stepUpToken) {
      throw new ApiError({
        status: 403,
        code: "STEP_UP_REQUIRED",
        message: "این عملیات نیازمند تأیید هویت مرحله‌دوم (PIN) است.",
      });
    }
    const index = mockOrders.findIndex((o) => o.id === id);
    if (index === -1) throw new ApiError({ status: 404, code: "NOT_FOUND", message: "Order not found" });
    mockOrders.splice(index, 1);
    recordAuditLog("soft_delete", "order", String(id));
    return delay(undefined);
  },

  async listCustomers(params: CustomerListParams = {}): Promise<CustomerListResponse> {
    let filtered = [...mockCustomers];
    if (params.search) {
      const q = params.search.trim().toLowerCase();
      filtered = filtered.filter(
        (c) =>
          c.phone.includes(q) ||
          (c.full_name?.toLowerCase().includes(q) ?? false),
      );
    }
    const skip = params.skip ?? 0;
    const limit = params.limit ?? 20;
    return delay({
      data: filtered.slice(skip, skip + limit),
      meta: {
        total_count: filtered.length,
        skip,
        limit,
        has_next: skip + limit < filtered.length,
        has_prev: skip > 0,
      },
    });
  },

  async getCustomer(id: number): Promise<CustomerDetail> {
    const customer = mockCustomers.find((c) => c.id === id);
    if (!customer) throw new ApiError({ status: 404, code: "NOT_FOUND", message: "Customer not found" });
    return delay(customer);
  },

  async updateCustomer(id: number, payload: CustomerUpdatePayload): Promise<CustomerDetail> {
    const customer = mockCustomers.find((c) => c.id === id);
    if (!customer) throw new ApiError({ status: 404, code: "NOT_FOUND", message: "Customer not found" });
    if (payload.full_name !== undefined) customer.full_name = payload.full_name;
    if (payload.is_active !== undefined) customer.is_active = payload.is_active;
    if (payload.note !== undefined) customer.note = payload.note;
    if (payload.category !== undefined) customer.category = payload.category;
    if (payload.tags !== undefined) customer.tags = payload.tags;
    return delay(customer);
  },

  async deleteCustomer(id: number, stepUpToken: string | null): Promise<void> {
    if (!stepUpToken) {
      throw new ApiError({
        status: 403,
        code: "STEP_UP_REQUIRED",
        message: "این عملیات نیازمند تأیید هویت مرحله‌دوم (PIN) است.",
      });
    }
    const index = mockCustomers.findIndex((c) => c.id === id);
    if (index === -1) throw new ApiError({ status: 404, code: "NOT_FOUND", message: "Customer not found" });
    mockCustomers.splice(index, 1);
    recordAuditLog("soft_delete", "user", String(id));
    return delay(undefined);
  },

  async listAuditLogs(params: AuditLogListParams = {}): Promise<AuditLogListResponse> {
    const { skip = 0, limit = 50, entity_type, entity_id } = params;
    let filtered = [...auditLogs];
    if (entity_type) filtered = filtered.filter((row) => row.entity_type === entity_type);
    if (entity_id) filtered = filtered.filter((row) => row.entity_id === entity_id);
    const total = filtered.length;
    return delay({
      data: filtered.slice(skip, skip + limit),
      meta: { total_count: total, skip, limit, has_next: skip + limit < total, has_prev: skip > 0 },
    });
  },

  async createCategory(payload: CategoryCreatePayload): Promise<CategoryFlat> {
    const flat = flattenCategoryTree(categories);
    const id = Math.max(0, ...flat.map((c) => c.id)) + 1;
    const row: CategoryFlat = {
      id,
      name: payload.name,
      parent_id: payload.parent_id ?? null,
      depth: payload.parent_id ? 2 : 1,
      is_leaf: true,
      is_selectable: false,
      breadcrumb: [payload.name],
      ancestor_ids: payload.parent_id ? [payload.parent_id] : [],
    };
    return delay(row);
  },

  async updateCategory(id: number, payload: CategoryUpdatePayload): Promise<CategoryFlat> {
    const flat = flattenCategoryTree(categories);
    const row = flat.find((c) => c.id === id);
    if (!row) throw new ApiError({ status: 404, code: "NOT_FOUND", message: "Category not found" });
    if (payload.name) row.name = payload.name;
    return delay(row);
  },

  async deleteCategory(id: number, stepUpToken: string | null): Promise<CategoryDeleteResult> {
    if (!stepUpToken) {
      throw new ApiError({ status: 403, code: "STEP_UP_REQUIRED", message: "Step-up required" });
    }
    const flat = flattenCategoryTree(categories);
    const category = flat.find((c) => c.id === id);
    if (!category) throw new ApiError({ status: 404, code: "NOT_FOUND", message: "دسته یافت نشد" });
    const child = flat.some((c) => c.parent_id === id);
    if (child) {
      throw new ApiError({
        status: 400,
        code: "BAD_REQUEST",
        message: "ابتدا زیردسته‌ها را حذف کنید",
      });
    }
    // Mock: remove from in-memory tree (best-effort leaf delete)
    const removeFromTree = (nodes: CategoryTreeNode[]): boolean => {
      const idx = nodes.findIndex((n) => n.id === id);
      if (idx >= 0) {
        nodes.splice(idx, 1);
        return true;
      }
      return nodes.some((n) => removeFromTree(n.subcategories));
    };
    removeFromTree(categories);
    return delay({
      id,
      products_reassigned: 0,
      new_category_id: null,
      message: "Empty category deleted; no product reassignment needed.",
    });
  },

  async verifyPin(pin: string): Promise<StepUpTokenResponse> {
    if (pin !== STATIC_ADMIN_PIN) {
      throw new ApiError({
        status: 403,
        code: "STEP_UP_INVALID",
        message: "کد امنیتی وارد شده نادرست است.",
        fieldErrors: { pin: "کد PIN صحیح نیست." },
      });
    }
    return delay({
      secure_token: `mock-step-up.${Date.now()}`,
      token_type: "step_up",
      expires_in: 300,
    });
  },

  async listArticles(params: ArticleListParams = {}): Promise<ArticleListResponse> {
    const { skip = 0, limit = 20, search, is_published } = params;
    let filtered = [...articles];
    if (search) {
      const q = search.trim().toLowerCase();
      filtered = filtered.filter(
        (a) => a.title.toLowerCase().includes(q) || a.slug.toLowerCase().includes(q),
      );
    }
    if (is_published !== undefined) {
      filtered = filtered.filter((a) => a.is_published === is_published);
    }
    filtered.sort((a, b) => new Date(b.published_at).getTime() - new Date(a.published_at).getTime());
    const total = filtered.length;
    return delay({
      data: filtered.slice(skip, skip + limit),
      meta: { total_count: total, skip, limit, has_next: skip + limit < total, has_prev: skip > 0 },
    });
  },

  async createArticle(payload: ArticleCreatePayload): Promise<Article> {
    const slug = payload.slug.trim();
    if (articles.some((a) => a.slug === slug)) {
      throw new ApiError({
        status: 409,
        code: "CONFLICT",
        message: `مقاله‌ای با اسلاگ «${slug}» از قبل ثبت شده است.`,
        fieldErrors: { slug: "این اسلاگ تکراری است." },
      });
    }
    const created: Article = {
      id: nextArticleId++,
      slug,
      title: payload.title.trim(),
      excerpt: payload.excerpt,
      cover_image: payload.cover_image ?? null,
      published_at: payload.published_at,
      reading_minutes: payload.reading_minutes,
      author: payload.author,
      tags: payload.tags ?? [],
      related_product_ids: payload.related_product_ids ?? [],
      blocks: payload.blocks ?? [],
      is_published: payload.is_published,
      created_at: nowIso(),
      updated_at: nowIso(),
    };
    articles.unshift(created);
    return delay(created);
  },

  async updateArticle(id: number, payload: ArticleUpdatePayload): Promise<Article> {
    const article = articles.find((a) => a.id === id);
    if (!article) throw new ApiError({ status: 404, code: "NOT_FOUND", message: "مقاله یافت نشد." });
    if (payload.slug !== undefined) article.slug = payload.slug.trim();
    if (payload.title !== undefined) article.title = payload.title.trim();
    if (payload.excerpt !== undefined) article.excerpt = payload.excerpt;
    if (payload.cover_image !== undefined) article.cover_image = payload.cover_image;
    if (payload.published_at !== undefined) article.published_at = payload.published_at;
    if (payload.reading_minutes !== undefined) article.reading_minutes = payload.reading_minutes;
    if (payload.author !== undefined) article.author = payload.author;
    if (payload.tags !== undefined) article.tags = payload.tags;
    if (payload.related_product_ids !== undefined) article.related_product_ids = payload.related_product_ids;
    if (payload.blocks !== undefined) article.blocks = payload.blocks;
    if (payload.is_published !== undefined) article.is_published = payload.is_published;
    article.updated_at = nowIso();
    return delay(article);
  },

  async deleteArticle(id: number, stepUpToken: string | null): Promise<void> {
    if (!stepUpToken) {
      throw new ApiError({
        status: 403,
        code: "STEP_UP_REQUIRED",
        message: "این عملیات نیازمند تأیید هویت مرحله‌دوم (PIN) است.",
      });
    }
    const index = articles.findIndex((a) => a.id === id);
    if (index === -1) throw new ApiError({ status: 404, code: "NOT_FOUND", message: "مقاله یافت نشد." });
    articles.splice(index, 1);
    return delay(undefined);
  },

  async listHeroSlides(params: HeroSlideListParams = {}): Promise<HeroSlideListResponse> {
    const { skip = 0, limit = 20, is_active } = params;
    let filtered = [...heroSlides];
    if (is_active !== undefined) filtered = filtered.filter((s) => s.is_active === is_active);
    filtered.sort((a, b) => a.sort_order - b.sort_order);
    const total = filtered.length;
    return delay({
      data: filtered.slice(skip, skip + limit),
      meta: { total_count: total, skip, limit, has_next: skip + limit < total, has_prev: skip > 0 },
    });
  },

  async createHeroSlide(payload: HeroSlideCreatePayload): Promise<HeroSlide> {
    const created: HeroSlide = {
      id: nextHeroSlideId++,
      title: payload.title.trim(),
      subtitle: payload.subtitle ?? null,
      cta_label: payload.cta_label ?? null,
      cta_href: payload.cta_href ?? null,
      image: payload.image,
      accent: payload.accent,
      sort_order: payload.sort_order,
      is_active: payload.is_active,
    };
    heroSlides.push(created);
    return delay(created);
  },

  async updateHeroSlide(id: number, payload: HeroSlideUpdatePayload): Promise<HeroSlide> {
    const slide = heroSlides.find((s) => s.id === id);
    if (!slide) throw new ApiError({ status: 404, code: "NOT_FOUND", message: "اسلاید یافت نشد." });
    if (payload.title !== undefined) slide.title = payload.title.trim();
    if (payload.subtitle !== undefined) slide.subtitle = payload.subtitle;
    if (payload.cta_label !== undefined) slide.cta_label = payload.cta_label;
    if (payload.cta_href !== undefined) slide.cta_href = payload.cta_href;
    if (payload.image !== undefined) slide.image = payload.image;
    if (payload.accent !== undefined) slide.accent = payload.accent;
    if (payload.sort_order !== undefined) slide.sort_order = payload.sort_order;
    if (payload.is_active !== undefined) slide.is_active = payload.is_active;
    return delay(slide);
  },

  async deleteHeroSlide(id: number, stepUpToken: string | null): Promise<void> {
    if (!stepUpToken) {
      throw new ApiError({
        status: 403,
        code: "STEP_UP_REQUIRED",
        message: "این عملیات نیازمند تأیید هویت مرحله‌دوم (PIN) است.",
      });
    }
    const index = heroSlides.findIndex((s) => s.id === id);
    if (index === -1) throw new ApiError({ status: 404, code: "NOT_FOUND", message: "اسلاید یافت نشد." });
    heroSlides.splice(index, 1);
    return delay(undefined);
  },

  async listProductComments(params: ProductCommentListParams = {}): Promise<ProductCommentListResponse> {
    const { skip = 0, limit = 20, product_id } = params;
    let filtered = [...productComments];
    if (product_id !== undefined) filtered = filtered.filter((c) => c.product_id === product_id);
    filtered.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    const total = filtered.length;
    return delay({
      data: filtered.slice(skip, skip + limit),
      meta: { total_count: total, skip, limit, has_next: skip + limit < total, has_prev: skip > 0 },
    });
  },

  async deleteProductComment(id: number, stepUpToken: string | null): Promise<void> {
    if (!stepUpToken) {
      throw new ApiError({
        status: 403,
        code: "STEP_UP_REQUIRED",
        message: "این عملیات نیازمند تأیید هویت مرحله‌دوم (PIN) است.",
      });
    }
    const index = productComments.findIndex((c) => c.id === id);
    if (index === -1) throw new ApiError({ status: 404, code: "NOT_FOUND", message: "نظر یافت نشد." });
    productComments.splice(index, 1);
    return delay(undefined);
  },

  async listContactSubmissions(
    params: ContactSubmissionListParams = {},
  ): Promise<ContactSubmissionListResponse> {
    const { skip = 0, limit = 20, search, phone } = params;
    let filtered = [...contactSubmissions];
    if (search) {
      const q = search.trim().toLowerCase();
      filtered = filtered.filter(
        (c) =>
          c.full_name.toLowerCase().includes(q) ||
          c.subject.toLowerCase().includes(q) ||
          c.ticket_code.toLowerCase().includes(q),
      );
    }
    if (phone) filtered = filtered.filter((c) => c.phone.includes(phone));
    filtered.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    const total = filtered.length;
    return delay({
      data: filtered.slice(skip, skip + limit),
      meta: { total_count: total, skip, limit, has_next: skip + limit < total, has_prev: skip > 0 },
    });
  },

  async login(payload: { phone_number: string; password: string }): Promise<Token> {
    const validPhone = MOCK_ADMIN_CREDENTIALS.phone;
    const validPassword = MOCK_ADMIN_CREDENTIALS.passwordHint;
    const requirePassword = getAdminSettings().require_password_for_login;

    const phoneOk = payload.phone_number.trim() === validPhone;
    const passwordOk = !requirePassword || payload.password === validPassword;

    if (!phoneOk || !passwordOk) {
      throw new ApiError({
        status: 401,
        code: "UNAUTHORIZED",
        message: "شماره موبایل یا رمز عبور نادرست است.",
        fieldErrors: { password: "اطلاعات ورود صحیح نیست." },
      });
    }

    return delay({
      access_token: "mock-admin-access-token",
      refresh_token: "mock-admin-refresh-token",
      token_type: "bearer",
      expires_in: 3600,
    });
  },
};
