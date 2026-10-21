/** Shared hero forensic capture helpers (Playwright + Chrome channel). */

export const SPLASH_STORAGE_KEY = "karzar-splash-seen";

export const SLIDES = [
  {
    id: "H01",
    title: "تخفیف‌های ویژه‌ی کارزار",
    desktop: "H01-special-offers-desktop-16x9.webp",
    mobile: "H01-special-offers-mobile-4x3.webp",
  },
  {
    id: "H02",
    title: "ابزار اندازه‌گیری",
    desktop: "H02-measuring-tools-desktop-16x9.webp",
    mobile: "H02-measuring-tools-mobile-4x3.webp",
  },
  {
    id: "H03",
    title: "اینسرت و ابزارهای اینسرتی",
    desktop: "H03-inserts-turning-tools-desktop-16x9.webp",
    mobile: "H03-inserts-turning-tools-mobile-4x3.webp",
  },
  {
    id: "H04",
    title: "فرز انگشتی",
    desktop: "H04-end-mills-desktop-16x9.webp",
    mobile: "H04-end-mills-mobile-4x3.webp",
  },
  {
    id: "H05",
    title: "دستگاه‌های صنعتی",
    desktop: "H05-industrial-machines-desktop-16x9.webp",
    mobile: "H05-industrial-machines-mobile-4x3.webp",
  },
];

export const MANDATORY_VIEWPORTS = [
  { w: 390, h: 844, dpr: 3, label: "390x844@3", compact: true },
  { w: 1023, h: 900, dpr: 2, label: "1023x900@2", compact: true },
  { w: 1024, h: 768, dpr: 2, label: "1024x768@2", compact: false },
  { w: 1440, h: 900, dpr: 2, label: "1440x900@2", compact: false },
  { w: 1920, h: 1080, dpr: 2, label: "1920x1080@2", compact: false },
];

export function heroImageLocator(page) {
  return page.locator(
    '[data-testid="campaign-hero-fullbleed"] picture img, [data-testid="campaign-hero-compact-media"] picture img',
  ).first();
}

export async function installPerfInstrumentation(page) {
  await page.addInitScript(() => {
    window.__karzarPerf = { lcp: [], navigationStart: null };
    try {
      const nav = performance.getEntriesByType("navigation")[0];
      window.__karzarPerf.navigationStart = nav ? nav.startTime : 0;
    } catch {
      window.__karzarPerf.navigationStart = 0;
    }
    try {
      const po = new PerformanceObserver((list) => {
        for (const e of list.getEntries()) {
          const el = e.element;
          const imgSrc =
            el && el.tagName === "IMG"
              ? el.currentSrc || el.src || ""
              : el && el.src
                ? el.src
                : "";
          window.__karzarPerf.lcp.push({
            startTime: e.startTime,
            renderTime: e.renderTime ?? null,
            loadTime: e.loadTime ?? null,
            size: e.size,
            url: e.url || imgSrc || "",
            id: e.id || "",
            tagName: el && el.tagName ? el.tagName : null,
            src: imgSrc || null,
            testId: el?.closest?.("[data-testid]")?.getAttribute?.("data-testid") ?? null,
          });
        }
      });
      po.observe({ type: "largest-contentful-paint", buffered: true });
    } catch {
      /* unsupported */
    }
  });
}

/** Splash is absent during React `boot` — do not treat `.karzar-splash` count 0 alone as dismissed. */
export async function waitSplashDismissed(page) {
  await page.waitForFunction(
    (key) => {
      let seen = false;
      try {
        seen = sessionStorage.getItem(key) === "1";
      } catch {
        return false;
      }
      if (!seen) return false;
      if (document.querySelectorAll(".karzar-splash").length > 0) return false;
      if (document.querySelectorAll("style[data-karzar-splash-boot]").length > 0) return false;
      return true;
    },
    SPLASH_STORAGE_KEY,
    { timeout: 35_000 },
  );
}

export async function assertHeroNotObscured(page) {
  await page.waitForFunction(
    () => {
      const region =
        document.querySelector('[data-testid="campaign-hero-fullbleed"]') ||
        document.querySelector('[data-testid="campaign-hero-compact"]');
      if (!region) return false;
      const rect = region.getBoundingClientRect();
      if (rect.width < 8 || rect.height < 8) return false;
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height * 0.35;
      const top = document.elementFromPoint(cx, cy);
      if (!top) return false;
      if (top.closest(".karzar-splash")) return false;
      return (
        region.contains(top) ||
        Boolean(
          top.closest('[data-testid="campaign-hero-fullbleed"], [data-testid="campaign-hero-compact"]'),
        )
      );
    },
    { timeout: 15_000 },
  );
}

export async function gotoHomeReady(page) {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("http://127.0.0.1:3000/", { waitUntil: "domcontentloaded", timeout: 120_000 });
  await page.getByRole("region", { name: "هیرو کارزار" }).waitFor({ state: "visible", timeout: 30_000 });
  await waitSplashDismissed(page);
  await assertHeroNotObscured(page);
}

export async function assertActiveSlide(page, slideIndex, compact) {
  const slide = SLIDES[slideIndex];
  if (!slide) throw new Error(`Invalid slide index ${slideIndex}`);

  if ((await page.locator(".karzar-splash").count()) > 0) {
    throw new Error(`Splash still present when capturing ${slide.id}`);
  }
  if ((await page.locator("style[data-karzar-splash-boot]").count()) > 0) {
    throw new Error(`Splash boot style still present when capturing ${slide.id}`);
  }

  const heroRegion = page.getByRole("region", { name: "هیرو کارزار" });
  await heroRegion.waitFor({ state: "visible" });

  if (compact) {
    await page.getByTestId("campaign-hero-compact").first().waitFor({ state: "visible" });
  } else {
    await page.getByTestId("campaign-hero-fullbleed").first().waitFor({ state: "visible" });
  }

  const heading = heroRegion.getByRole("heading", { name: slide.title, exact: true });
  await heading.waitFor({ state: "visible", timeout: 20_000 });
  await assertHeroNotObscured(page);

  const expectedAsset = compact ? slide.mobile : slide.desktop;
  const img = heroImageLocator(page);
  await img.waitFor({ state: "visible", timeout: 20_000 });

  await page.waitForFunction(
    ({ expectedAsset }) => {
      const node = document.querySelector(
        '[data-testid="campaign-hero-fullbleed"] picture img, [data-testid="campaign-hero-compact-media"] picture img',
      );
      if (!node) return false;
      const image = node;
      return (
        image.complete &&
        image.naturalWidth > 0 &&
        image.currentSrc.includes(expectedAsset) &&
        image.currentSrc.includes("pack-20261021")
      );
    },
    { expectedAsset },
    { timeout: 25_000 },
  );

  const currentSrc = await img.evaluate((n) => n.currentSrc);
  if (!currentSrc.includes(expectedAsset)) {
    throw new Error(`${slide.id}: expected asset ${expectedAsset} in ${currentSrc}`);
  }

  return { slide, expectedAsset, currentSrc, img, heroRegion };
}

export async function advanceOneSlide(page) {
  const before = await heroImageLocator(page).evaluate((n) => n.currentSrc);
  const region = page.getByRole("region", { name: "هیرو کارزار" });
  await region.focus();
  await page.keyboard.press("ArrowLeft");
  await page.waitForFunction(
    (prev) => {
      const node = document.querySelector(
        '[data-testid="campaign-hero-fullbleed"] picture img, [data-testid="campaign-hero-compact-media"] picture img',
      );
      return node && node.currentSrc && node.currentSrc !== prev && node.complete && node.naturalWidth > 0;
    },
    before,
    { timeout: 20_000 },
  );
}

export async function collectSlideMetrics(page, slideIndex, compact, viewportLabel) {
  const slide = SLIDES[slideIndex];
  const img = heroImageLocator(page);
  const metrics = await page.evaluate(() => {
    const compactLayout = !!document.querySelector('[data-testid="campaign-hero-compact"]');
    const node = document.querySelector(
      '[data-testid="campaign-hero-fullbleed"] picture img, [data-testid="campaign-hero-compact-media"] picture img',
    );
    if (!node) return null;
    const cs = getComputedStyle(node);
    const rect = node.getBoundingClientRect();
    const picture = node.closest("picture");
    const mobileSource = picture?.querySelector("source");
    return {
      compact: compactLayout,
      currentSrc: node.currentSrc,
      naturalWidth: node.naturalWidth,
      naturalHeight: node.naturalHeight,
      clientWidth: Math.round(rect.width),
      clientHeight: Math.round(rect.height),
      dpr: window.devicePixelRatio,
      objectFit: cs.objectFit,
      objectPosition: cs.objectPosition,
      mobileMedia: mobileSource?.getAttribute("media") ?? null,
      loading: node.loading,
      fetchPriority: node.fetchPriority,
    };
  });
  const perf = await page.evaluate(() => {
    const bag = window.__karzarPerf || { lcp: [], navigationStart: 0 };
    const hero = document.querySelector(
      '[data-testid="campaign-hero-fullbleed"] picture img, [data-testid="campaign-hero-compact-media"] picture img',
    );
    const last = bag.lcp.length ? bag.lcp[bag.lcp.length - 1] : null;
    let lcpTransferSize = null;
    if (last?.url) {
      const res = performance
        .getEntriesByType("resource")
        .find((r) => r.name === last.url || r.name === last.src);
      if (res) lcpTransferSize = res.transferSize ?? null;
    }
    const lcpIsHeroImage =
      !!last &&
      !!hero &&
      (last.url === hero.currentSrc ||
        last.src === hero.currentSrc ||
        (last.tagName === "IMG" &&
          hero ===
            document.querySelector(
              '[data-testid="campaign-hero-fullbleed"] picture img, [data-testid="campaign-hero-compact-media"] picture img',
            )));
    return { bag, last, lcpTransferSize, lcpIsHeroImage, heroCurrentSrc: hero?.currentSrc ?? "" };
  });
  const lastLcp = perf.last;
  return {
    slideId: slide.id,
    slideIndex,
    slideTitle: slide.title,
    expectedDesktop: slide.desktop,
    expectedMobile: slide.mobile,
    expectedAsset: compact ? slide.mobile : slide.desktop,
    viewport: viewportLabel,
    splashAbsent: true,
    ...metrics,
    lcpLast: lastLcp,
    lcpTransferSize: perf.lcpTransferSize,
    lcpIsHeroImage: perf.lcpIsHeroImage,
    heroCurrentSrcAtCapture: perf.heroCurrentSrc,
  };
}

export function median(nums) {
  const s = [...nums].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}
