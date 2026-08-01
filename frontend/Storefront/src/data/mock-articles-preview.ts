/**
 * Storefront article preview mocks — rich enough for blog listing, home «پربازدید»,
 * category rails, and pagination (≥20/page). Local covers only (SafeImage allowlist).
 *
 * Used when NEXT_PUBLIC_USE_MOCK=true OR when live `/blog/` returns an empty list.
 */

import type { Article, BlogBlock, BlogPost } from "@/types/content";

const COVER = (seed: string) =>
  `/images/placeholders/karzar-editorial.svg?v=${encodeURIComponent(seed)}`;

/** Five soft categories (first tag) for carousel rails. */
export const MOCK_ARTICLE_CATEGORIES = [
  "اندازه‌گیری",
  "ابزار برقی",
  "ایمنی کارگاه",
  "راهنمای خرید",
  "تراشکاری",
] as const;

type Seed = {
  slug: string;
  title: string;
  excerpt: string;
  category: (typeof MOCK_ARTICLE_CATEGORIES)[number];
  views: number;
  /** Days before 2026-08-02 (preview “today”). */
  daysAgo: number;
  reading_minutes: number;
  author?: string;
};

const SEEDS: Seed[] = [
  {
    slug: "digital-caliper-workshop-pick",
    title: "کولیس دیجیتال کارگاهی؛ چه دقتی واقعاً کافی است؟",
    excerpt:
      "معیار انتخاب دقت خواندن، بازه و شرایط محیط برای کنترل ابعادی روزمره در کارگاه تراشکاری.",
    category: "اندازه‌گیری",
    views: 18420,
    daysAgo: 2,
    reading_minutes: 8,
  },
  {
    slug: "micrometer-vs-caliper",
    title: "میکرومتر یا کولیس؟ کی کدام را بردارید",
    excerpt:
      "مقایسه کاربردی دو ابزار اندازه‌گیری برای تلرانس‌های تنگ و کنترل سریع روی میز کار.",
    category: "اندازه‌گیری",
    views: 15200,
    daysAgo: 5,
    reading_minutes: 7,
  },
  {
    slug: "choose-hammer-drill",
    title: "راهنمای انتخاب دریل چکشی مناسب بتن و مصالح سخت",
    excerpt:
      "توان، ضربه در دقیقه و ارگونومی؛ چک‌لیست خرید دریل چکشی برای نصاب و کارگاه ساختمانی.",
    category: "ابزار برقی",
    views: 22150,
    daysAgo: 1,
    reading_minutes: 9,
  },
  {
    slug: "cordless-drill-battery-tips",
    title: "باتری دریل شارژی را چطور نگه دارید تا عمرش کم نشود",
    excerpt:
      "شارژ، دمای محیط و نگهداری بلندمدت باتری‌های لیتیومی ابزار شارژی.",
    category: "ابزار برقی",
    views: 9800,
    daysAgo: 12,
    reading_minutes: 5,
  },
  {
    slug: "angle-grinder-disc-safety",
    title: "دیسک فرز؛ نصب درست و اشتباهات خطرناک",
    excerpt:
      "جهت چرخش، فلنج، محافظ و نکات ایمنی هنگام تعویض دیسک سنگ فرز.",
    category: "ایمنی کارگاه",
    views: 16780,
    daysAgo: 3,
    reading_minutes: 6,
  },
  {
    slug: "ppe-workshop-basics",
    title: "حداقل تجهیزات حفاظت فردی برای کار با ابزار برقی",
    excerpt:
      "عینک، گوشی، دستکش و لباس کار؛ اولویت‌بندی محافظت در کارگاه کوچک و صنعتی.",
    category: "ایمنی کارگاه",
    views: 11240,
    daysAgo: 8,
    reading_minutes: 6,
  },
  {
    slug: "buying-digital-caliper-checklist",
    title: "چک‌لیست خرید کولیس دیجیتال بدون پشیمانی",
    excerpt:
      "بازه، وضوح نمایشگر، ضدآب بودن و خدمات؛ قبل از خرید چه بپرسید.",
    category: "راهنمای خرید",
    views: 13450,
    daysAgo: 4,
    reading_minutes: 7,
  },
  {
    slug: "insert-tool-holder-basics",
    title: "هلدر اینسرتی؛ شروع کار برای تراشکار تازه‌کار",
    excerpt:
      "شناخت هندسه اینسرت، گیره و مسیر براده برای تراشکاری پایدارتر.",
    category: "تراشکاری",
    views: 8900,
    daysAgo: 9,
    reading_minutes: 10,
  },
  {
    slug: "vernier-caliper-reading",
    title: "آموزش خواندن کولیس ورنیه قدم‌به‌قدم",
    excerpt:
      "مقیاس اصلی و ورنیه؛ تمرین خواندن صدم میلی‌متر بدون سردرگمی.",
    category: "اندازه‌گیری",
    views: 20110,
    daysAgo: 6,
    reading_minutes: 11,
  },
  {
    slug: "lathe-cutting-speed-intro",
    title: "سرعت برش در تراشکاری؛ از کجا شروع کنیم",
    excerpt:
      "رابطه دور اسپیندل، قطر قطعه و جنس ابزار برای براده‌برداری تمیز.",
    category: "تراشکاری",
    views: 7650,
    daysAgo: 14,
    reading_minutes: 8,
  },
  {
    slug: "die-grinder-uses",
    title: "فرز انگشتی کجا می‌درخشد؟ کاربردهای کارگاهی",
    excerpt:
      "پلیسه‌گیری، پرداخت و دسترسی به نقاط تنگ با فرز انگشتی پنوماتیک یا برقی.",
    category: "ابزار برقی",
    views: 6540,
    daysAgo: 11,
    reading_minutes: 5,
  },
  {
    slug: "tap-drill-size-guide",
    title: "انتخاب مته قبل از قلاویز؛ اشتباه رایج و راه‌حل",
    excerpt:
      "چرا قطر سوراخ پیش‌قلاویز مهم است و چطور از شکستن قلاویز کم کنید.",
    category: "تراشکاری",
    views: 14320,
    daysAgo: 7,
    reading_minutes: 7,
  },
  {
    slug: "workshop-dust-and-noise",
    title: "گردوغبار و صدا در کارگاه؛ کنترل ساده اما مؤثر",
    excerpt:
      "تهویه موضعی، زمان استراحت شنوایی و عادت‌های روزانه برای کار طولانی.",
    category: "ایمنی کارگاه",
    views: 4320,
    daysAgo: 18,
    reading_minutes: 5,
  },
  {
    slug: "buy-bench-vise",
    title: "گیره رومیزی؛ دهانه، وزن و پایه مناسب میز کار",
    excerpt:
      "راهنمای خرید گیره برای قفل کردن قطعه در سوراخ‌کاری و سوهان‌کاری.",
    category: "راهنمای خرید",
    views: 5780,
    daysAgo: 15,
    reading_minutes: 6,
  },
  {
    slug: "height-gauge-shop-floor",
    title: "ارتفاع‌سنج در کنترل کیفیت کارگاهی",
    excerpt:
      "چه وقت ارتفاع‌سنج جای کولیس را می‌گیرد و نکات کالیبراسیون سریع.",
    category: "اندازه‌گیری",
    views: 3910,
    daysAgo: 20,
    reading_minutes: 6,
  },
  {
    slug: "impact-driver-vs-drill",
    title: "پیچ‌بند ضربه‌ای با دریل شارژی چه فرقی دارد؟",
    excerpt:
      "گشتاور، کاربرد پیچ‌کاری سنگین و انتخاب ابزار درست برای مونتاژ.",
    category: "ابزار برقی",
    views: 11900,
    daysAgo: 10,
    reading_minutes: 6,
  },
  {
    slug: "coolant-basics-machining",
    title: "روانکار و خنک‌کاری؛ حداقل دانستنی تراشکار",
    excerpt:
      "نقش خنک‌کننده روی عمر ابزار و کیفیت سطح؛ انتخاب ابتدایی برای کارگاه.",
    category: "تراشکاری",
    views: 5100,
    daysAgo: 16,
    reading_minutes: 7,
  },
  {
    slug: "buy-angle-grinder",
    title: "خرید سنگ فرز؛ توان، دیسک و سوئیچ ایمنی",
    excerpt:
      "چک‌لیست خرید فرز برای برش و سایش؛ چه مشخصاتی ارزش هزینه بیشتر دارند.",
    category: "راهنمای خرید",
    views: 16200,
    daysAgo: 3,
    reading_minutes: 8,
  },
  {
    slug: "lockout-power-tools",
    title: "قطع ایمن برق ابزار قبل از تعمیر و تعویض قطعه",
    excerpt:
      "عادت‌های ساده lockout برای جلوگیری از استارت ناخواسته در تعمیرات کارگاهی.",
    category: "ایمنی کارگاه",
    views: 2870,
    daysAgo: 22,
    reading_minutes: 4,
  },
  {
    slug: "bore-gauge-intro",
    title: "گیج داخل‌سنج؛ اندازه‌گیری قطر داخلی بدون دردسر",
    excerpt:
      "کاربرد گیج ساعتی داخل‌سنج در کنترل بوش و سیلندرهای ماشین‌کاری‌شده.",
    category: "اندازه‌گیری",
    views: 4480,
    daysAgo: 19,
    reading_minutes: 7,
  },
  {
    slug: "endmill-selection-start",
    title: "انتخاب فرز انگشتی فرزکاری؛ تعداد لبه و پوشش",
    excerpt:
      "شروع منطقی برای آلومینیوم و فولاد نرم؛ از کجا تعداد فلوت را انتخاب کنید.",
    category: "تراشکاری",
    views: 9200,
    daysAgo: 13,
    reading_minutes: 9,
  },
  {
    slug: "buy-measuring-set",
    title: "ست اندازه‌گیری کارگاهی برای شروع کسب‌وکار کوچک",
    excerpt:
      "حداقل ابزارهای اندازه‌گیری که یک کارگاه نوپا واقعاً لازم دارد.",
    category: "راهنمای خرید",
    views: 10550,
    daysAgo: 8,
    reading_minutes: 6,
  },
  {
    slug: "grinder-guard-must",
    title: "چرا برداشتن محافظ فرز ممنوع است؟",
    excerpt:
      "ریسک پاشش دیسک و براده؛ توضیح کوتاه برای اپراتور و سرپرست کارگاه.",
    category: "ایمنی کارگاه",
    views: 13400,
    daysAgo: 5,
    reading_minutes: 4,
  },
  {
    slug: "cordless-vs-corded-workshop",
    title: "شارژی یا سیم‌دار؟ انتخاب ابزار برقی برای کارگاه ثابت",
    excerpt:
      "مزایای هر کدام برای سوراخ‌کاری روزمره و کارهای سنگین روی میز ثابت.",
    category: "ابزار برقی",
    views: 8700,
    daysAgo: 17,
    reading_minutes: 5,
  },
  {
    slug: "surface-plate-care",
    title: "نگهداری صفحه صافی و بلوک‌های پایه‌ای",
    excerpt:
      "تمیزکاری، جلوگیری از ضربه و زمان‌بندی کالیبراسیون صفحه گرانیتی.",
    category: "اندازه‌گیری",
    views: 3120,
    daysAgo: 24,
    reading_minutes: 5,
  },
  {
    slug: "heli-coil-repair-intro",
    title: "هلی‌کویل؛ تعمیر رزوه آسیب‌دیده بدون تعویض قطعه",
    excerpt:
      "چه وقت تعمیر رزوه با هلی‌کویل به‌صرفه‌تر از ساخت قطعه جدید است.",
    category: "تراشکاری",
    views: 6890,
    daysAgo: 12,
    reading_minutes: 8,
  },
  {
    slug: "buy-tap-set",
    title: "ست قلاویز دستی؛ چه شماره‌هایی را اول بخرید",
    excerpt:
      "اولویت رزوه متریک رایج و جنس قلاویز برای چدن و فولاد نرم.",
    category: "راهنمای خرید",
    views: 7540,
    daysAgo: 21,
    reading_minutes: 6,
  },
  {
    slug: "eye-protection-grinding",
    title: "حفاظت چشم هنگام سنگ‌زنی و برش دیسکی",
    excerpt:
      "عینک در برابر شیلد؛ انتخاب درست برای کار با فرز و سنگ رومیزی.",
    category: "ایمنی کارگاه",
    views: 5400,
    daysAgo: 25,
    reading_minutes: 4,
  },
  {
    slug: "drill-bit-materials",
    title: "جنس مته؛ HSS، کبالت و کارباید به زبان ساده",
    excerpt:
      "برای فولاد، استیل و مصالح بنایی کدام مته دوام بیشتری می‌دهد.",
    category: "ابزار برقی",
    views: 12880,
    daysAgo: 6,
    reading_minutes: 7,
  },
  {
    slug: "shop-floor-5s-tools",
    title: "۵اس ابزارها؛ چیدمان میز کار برای سرعت و ایمنی",
    excerpt:
      "جای‌گذاری دریل، کولیس و آچارها طوری که هم پیدا شوند هم زمین نخورند.",
    category: "ایمنی کارگاه",
    views: 2650,
    daysAgo: 28,
    reading_minutes: 5,
  },
  {
    slug: "indicator-dial-setup",
    title: "ساعت اندازه‌گیری؛ هم‌محوری و کنترل لنگی",
    excerpt:
      "نصب پایه مغناطیسی و خواندن ساعت برای تنظیم سه نظام و فیکسچر.",
    category: "اندازه‌گیری",
    views: 8120,
    daysAgo: 11,
    reading_minutes: 8,
  },
  {
    slug: "buy-first-lathe-tooling",
    title: "اولین ست ابزار تراشکاری؛ از کجا شروع کنیم",
    excerpt:
      "هلدر، اینسرت عمومی و اندازه‌گیری‌های ضروری برای تراش رومیزی یا صنعتی کوچک.",
    category: "راهنمای خرید",
    views: 14900,
    daysAgo: 2,
    reading_minutes: 9,
  },
];

const PREVIEW_ORIGIN = Date.UTC(2026, 7, 2, 10, 0, 0); // 2026-08-02

function toIsoDaysAgo(daysAgo: number): string {
  return new Date(PREVIEW_ORIGIN - daysAgo * 86_400_000).toISOString();
}

type SectionSeed = { title: string; body: string; bullets?: string[] };

/** Category-aware section outlines so mock detail pages have a real TOC. */
function sectionsFor(seed: Seed): SectionSeed[] {
  const topic = seed.title.replace(/[؟?]/g, "").trim();
  switch (seed.category) {
    case "اندازه‌گیری":
      return [
        {
          title: "چرا این اندازه‌گیری مهم است",
          body: `${seed.excerpt} در کنترل ابعادی کارگاهی، انتخاب ابزار درست از دوباره‌کاری و ضایعات جلوگیری می‌کند.`,
        },
        {
          title: "معیارهای انتخاب ابزار",
          body: `برای موضوع «${topic}» دقت خواندن، بازهٔ اندازه‌گیری، پایداری فک‌ها و شرایط محیط (روغن، براده، دما) را هم‌زمان ببینید.`,
          bullets: [
            "تلرانس نقشه را قبل از خرید مشخص کنید.",
            "وضوح نمایشگر یا ورنیه را با نیاز واقعی تطبیق دهید.",
            "در صورت کار تر یا روغنی، محافظت و قفل صفر را بررسی کنید.",
          ],
        },
        {
          title: "نکتهٔ کارگاهی",
          body: "ابزار اندازه‌گیری را از ضربه و افتادن دور نگه دارید و صفر را روی سطح تمیز و پایدار تنظیم کنید.",
        },
        {
          title: "جمع‌بندی",
          body: "با مشخص بودن قطعه و تلرانس، از کاتالوگ کارزار مدل مناسب را انتخاب کنید و مشخصات واقعی محصول را مبنا قرار دهید.",
        },
      ];
    case "ابزار برقی":
      return [
        {
          title: "کاربرد اصلی در کارگاه",
          body: `${seed.excerpt} توان، دور، ارگونومی و نوع تغذیه (شارژی یا سیم‌دار) باید با الگوی کار روزانه هم‌خوان باشد.`,
        },
        {
          title: "چه مشخصاتی را اول چک کنید",
          body: `در انتخاب مرتبط با «${topic}»، گشتاور یا ضربه، وزن ابزار، نوع سه نظام و دسترسی به خدمات را اولویت دهید.`,
          bullets: [
            "توان را با جنس قطعه و عمق کار تطبیق دهید.",
            "برای شیفت‌های طولانی، وزن و لرزش مهم‌تر از عدد روی جعبه است.",
            "باتری و شارژر را بخشی از هزینهٔ واقعی بدانید.",
          ],
        },
        {
          title: "ایمنی هنگام کار",
          body: "محافظ، قفل سوئیچ و عادت قطع برق قبل از تعویض متعلقات را جدی بگیرید؛ سرعت کار نباید ایمنی را کم کند.",
        },
        {
          title: "جمع‌بندی خرید",
          body: "مدل را با نیاز واقعی بسنجید، نه فقط با بالاترین وات. مشخصات ثبت‌شده در کاتالوگ کارزار مرجع تصمیم است.",
        },
      ];
    case "ایمنی کارگاه":
      return [
        {
          title: "ریسک‌های رایج",
          body: `${seed.excerpt} بیشتر حوادث کارگاهی از عادت‌های ساده و حذف تجهیزات حفاظت فردی شروع می‌شود.`,
        },
        {
          title: "حداقل اقدامات عملی",
          body: `برای موضوع «${topic}» ابتدا منبع خطر را بشناسید، بعد حفاظت فردی و قفل ایمن ابزار را ثابت کنید.`,
          bullets: [
            "عینک، گوشی و دستکش مناسب کار را حذف نکنید.",
            "محافظ ابزار را برای «دسترسی بهتر» برندارید.",
            "قبل از تعمیر، برق یا باد را قطع و قفل کنید.",
          ],
        },
        {
          title: "عادت روزانه سرپرست",
          body: "یک چک کوتاه شروع شیفت (محافظ، کابل، دیسک، تهویه) هزینهٔ کمی دارد و از توقف اضطراری جلوگیری می‌کند.",
        },
        {
          title: "جمع‌بندی",
          body: "ایمنی بخشی از کیفیت کار است. رویه‌های ساده را مکتوب کنید و ابزار مناسب را از مسیر مطمئن تأمین کنید.",
        },
      ];
    case "راهنمای خرید":
      return [
        {
          title: "قبل از خرید چه بدانید",
          body: `${seed.excerpt} بدون تعریف قطعه، بودجه و شرایط کار، مقایسهٔ مدل‌ها گمراه‌کننده می‌شود.`,
        },
        {
          title: "چک‌لیست مقایسه",
          body: `برای «${topic}» مشخصات کلیدی، گارانتی، موجودی قطعات مصرفی و تناسب با بقیهٔ ست کارگاه را کنار هم بگذارید.`,
          bullets: [
            "نیاز واقعی را از «خواستهٔ تبلیغاتی» جدا کنید.",
            "خدمات پس از فروش و قطعات یدکی را بپرسید.",
            "قیمت را با عمر مفید و دقت/توان واقعی بسنجید.",
          ],
        },
        {
          title: "اشتباهات رایج خریدار",
          body: "خرید صرفاً بر اساس برند یا کمترین قیمت، بدون تطبیق با نقشه و کاربری، معمولاً به تعویض زودهنگام می‌انجامد.",
        },
        {
          title: "جمع‌بندی",
          body: "با چک‌لیست کوتاه و مشخصات واقعی کاتالوگ کارزار، انتخاب شفاف‌تری خواهید داشت.",
        },
      ];
    case "تراشکاری":
      return [
        {
          title: "زمینهٔ کارگاهی",
          body: `${seed.excerpt} در تراشکاری، هندسه ابزار، سرعت برش و صلبیت گیرش قطعه با هم کیفیت سطح را می‌سازند.`,
        },
        {
          title: "پارامترهایی که باید تنظیم کنید",
          body: `در ارتباط با «${topic}»، جنس قطعه، عمق براده، خنک‌کاری و وضعیت هلدر/اینسرت را قبل از افزایش دور بررسی کنید.`,
          bullets: [
            "از اینسرت و هلدر متناسب با عملیات شروع کنید.",
            "دور و پیشروی را پله‌ای بالا ببرید، نه یک‌باره.",
            "لرزش و صدای غیرعادی را جدی بگیرید.",
          ],
        },
        {
          title: "کنترل کیفیت سریع",
          body: "بعد از چند پاس اول، اندازه و کیفیت سطح را با ابزار اندازه‌گیری مناسب چک کنید تا مسیر براده اصلاح شود.",
        },
        {
          title: "جمع‌بندی",
          body: "شروع محافظه‌کارانه و اندازه‌گیری منظم، پایدارتر از حداکثر کردن نرخ براده‌برداری است. ابزار را از کاتالوگ معتبر انتخاب کنید.",
        },
      ];
    default:
      return [
        {
          title: "مقدمه",
          body: seed.excerpt,
        },
        {
          title: "نکتهٔ کارگاهی",
          body: "قبل از خرید، قطعه و شرایط کار را مشخص کنید و از مشخصات واقعی محصول استفاده کنید.",
        },
      ];
  }
}

function buildMockBlocks(seed: Seed): BlogBlock[] {
  const blocks: BlogBlock[] = [
    {
      type: "paragraph",
      text: "در این مطلب مجله کارزار، موضوع را به‌صورت بخش‌بندی‌شده مرور می‌کنیم تا برای کارگاه و خرید، مسیر تصمیم روشن‌تری داشته باشید.",
    },
  ];

  for (const section of sectionsFor(seed)) {
    blocks.push({ type: "heading", text: section.title });
    blocks.push({ type: "paragraph", text: section.body });
    if (section.bullets?.length) {
      blocks.push({ type: "list", items: section.bullets });
    }
  }

  blocks.push({
    type: "callout",
    variant: "note",
    text: "نسخهٔ پیش‌نمایش مجله برای تست طراحی فروشگاه است؛ متن آموزشی کامل به‌تدریج از پنل محتوا جایگزین می‌شود.",
  });

  return blocks;
}

function seedToPost(seed: Seed, id: number): BlogPost {
  const tags = [seed.category, "مجله کارزار", "ابزار صنعتی"];
  return {
    id,
    slug: seed.slug,
    title: seed.title,
    excerpt: seed.excerpt,
    cover_image: COVER(`article-${seed.slug}`),
    published_at: toIsoDaysAgo(seed.daysAgo),
    reading_minutes: seed.reading_minutes,
    views: seed.views,
    tags,
    author: seed.author ?? "تیم فنی کارزار",
    related_product_ids: [],
    blocks: buildMockBlocks(seed),
  };
}

/** Full mock posts for listing + detail fallback (32 items). */
export const MOCK_ARTICLE_POSTS: BlogPost[] = SEEDS.map((seed, index) =>
  seedToPost(seed, 9000 + index + 1),
);

const BY_SLUG = new Map(MOCK_ARTICLE_POSTS.map((p) => [p.slug, p]));

export function listMockArticleTeasers(): Article[] {
  return MOCK_ARTICLE_POSTS.map(
    ({
      id,
      slug,
      title,
      excerpt,
      cover_image,
      published_at,
      reading_minutes,
      tags,
      views,
    }) => ({
      id,
      slug,
      title,
      excerpt,
      cover_image,
      published_at,
      reading_minutes,
      tags,
      views,
    }),
  );
}

export function getMockArticlePost(slug: string | null | undefined): BlogPost | null {
  if (!slug) return null;
  return BY_SLUG.get(slug) ?? null;
}

export const MOCK_ARTICLE_COUNT = MOCK_ARTICLE_POSTS.length;
