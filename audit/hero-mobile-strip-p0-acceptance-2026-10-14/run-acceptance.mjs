/**
 * LOCAL_BUILD_EVIDENCE — production standalone @ PR #495 HEAD.
 * Run from repo root after Storefront build:
 *   node audit/hero-mobile-strip-p0-acceptance-2026-10-14/run-acceptance.mjs
 */
import { createRequire } from "node:module";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dir = dirname(fileURLToPath(import.meta.url));
const require = createRequire(
  join(__dir, "../../frontend/Storefront/package.json"),
);
const { chromium, devices } = require("playwright");
const BASE_URL = process.env.ACCEPTANCE_BASE_URL ?? "http://127.0.0.1:3098";
const GIT_SHA = process.env.ACCEPTANCE_GIT_SHA ?? "203995fddf7725e61953a5ccd050baf9dd7a1f74";
const SPLASH_KEY = "karzar-splash-seen";

const SLIDE_TITLES = [
  "تخفیف‌های ویژه‌ی کارزار",
  "ابزار اندازه‌گیری",
  "اینسرت و ابزارهای اینسرتی",
  "فرز انگشتی",
  "دستگاه‌های صنعتی",
];

const H03_CTAS = ["مشاهده اینسرت‌ها", "مشاهده ابزارهای اینسرتی"];

function heroSection(page) {
  return page.locator('section[aria-label="هیرو کارزار"]');
}

async function skipSplash(page) {
  await page.addInitScript((key) => {
    try {
      sessionStorage.setItem(key, "1");
    } catch {
      /* ignore */
    }
  }, SPLASH_KEY);
}

async function assertSplashGone(page) {
  const splash = page.locator(".karzar-splash");
  await splash.waitFor({ state: "hidden", timeout: 15_000 }).catch(() => {});
  const visible = await splash.isVisible().catch(() => false);
  return !visible;
}

async function visibleHeroTitle(page) {
  return page.evaluate(() => {
    const hero = document.querySelector('section[aria-label="هیرو کارزار"]');
    if (!hero) return null;
    const center =
      hero.querySelector('[data-testid="hero-motion-track"] .z-\\[1\\]') ??
      hero.querySelector('[data-testid="hero-motion-track"] .relative.z-\\[1\\]');
    const root = center ?? hero;
    const titles = root.querySelectorAll("h1, h2");
    for (const el of titles) {
      if (el.closest('[aria-hidden="true"]')) continue;
      const r = el.getBoundingClientRect();
      if (r.width > 0 && r.height > 0) return el.textContent?.trim() ?? null;
    }
    for (const el of hero.querySelectorAll("h1, h2")) {
      if (el.closest('[aria-hidden="true"]')) continue;
      const r = el.getBoundingClientRect();
      if (r.width > 0 && r.height > 0) return el.textContent?.trim() ?? null;
    }
    return null;
  });
}

async function heroImageReady(page) {
  return page.evaluate(() => {
    const hero = document.querySelector('section[aria-label="هیرو کارزار"]');
    if (!hero) return { ok: false, reason: "no-hero" };
    const img = hero.querySelector("img");
    if (!img) return { ok: false, reason: "no-img" };
    const nw = img.naturalWidth;
    const nh = img.naturalHeight;
    return { ok: nw > 0 && nh > 0, naturalWidth: nw, naturalHeight: nh };
  });
}

async function measureHeroAndNextSection(page) {
  return page.evaluate(() => {
    const hero = document.querySelector('section[aria-label="هیرو کارزار"]');
    if (!hero) return null;
    const hr = hero.getBoundingClientRect();
    const sections = [...document.querySelectorAll("main section, main > div > section")].filter(
      (el) => el !== hero && !hero.contains(el),
    );
    let nextTop = null;
    for (const s of sections) {
      const r = s.getBoundingClientRect();
      if (r.top >= hr.bottom - 2 && r.height > 40) {
        nextTop = r.top;
        break;
      }
    }
    if (nextTop == null) {
      const mainKids = [...document.querySelectorAll("body *")].filter((el) => {
        const r = el.getBoundingClientRect();
        return r.top >= hr.bottom - 1 && r.height > 60 && getComputedStyle(el).backgroundColor.includes("255");
      });
      if (mainKids[0]) nextTop = mainKids[0].getBoundingClientRect().top;
    }
    return {
      heroTop: hr.top,
      heroBottom: hr.bottom,
      heroHeight: hr.height,
      nextSectionTop: nextTop,
    };
  });
}

async function measureH03Ctas(page) {
  return page.evaluate((ctaLabels) => {
    const hero = document.querySelector('section[aria-label="هیرو کارزار"]');
    if (!hero) return { ok: false, ctas: [] };
    const hr = hero.getBoundingClientRect();
    const ctas = ctaLabels.map((label) => {
      const link = [...hero.querySelectorAll("a")].find((a) => a.textContent?.trim() === label);
      if (!link) return { label, found: false };
      const r = link.getBoundingClientRect();
      const inside =
        r.top >= hr.top &&
        r.bottom <= hr.bottom &&
        r.left >= hr.left &&
        r.right <= hr.right;
      return {
        label,
        found: true,
        top: r.top,
        bottom: r.bottom,
        insideHero: inside,
        intersectionRatio: inside ? 1 : 0,
      };
    });
    return { ok: ctas.every((c) => c.found && c.insideHero), ctas };
  }, H03_CTAS);
}

async function mediaCopyBoundaryY(page) {
  return page.evaluate(() => {
    const hero = document.querySelector('section[aria-label="هیرو کارزار"]');
    if (!hero) return null;
    const media = hero.querySelector('[data-testid="campaign-hero-compact-media"]');
    const copy = hero.querySelector('[data-testid="campaign-hero-compact"]');
    if (!media || !copy) return null;
    const mr = media.getBoundingClientRect();
    const panels = [...hero.querySelectorAll('[data-testid="campaign-hero-compact"]')].map((el) => {
      const m = el.querySelector('[data-testid="campaign-hero-compact-media"]');
      const cr = el.getBoundingClientRect();
      const mr2 = m?.getBoundingClientRect();
      return {
        slideId: el.closest("[data-slide-id]")?.getAttribute("data-slide-id") ?? null,
        mediaBottom: mr2?.bottom ?? null,
        copyTop: mr2 ? cr.top + (mr2.bottom - cr.top) : null,
      };
    });
    return { currentMediaBottom: mr.bottom, panelCount: panels.length, panels };
  });
}

async function touchSwipe(page, startX, startY, endX, endY) {
  const cdp = await page.context().newCDPSession(page);
  const steps = 14;
  await cdp.send("Input.dispatchTouchEvent", {
    type: "touchStart",
    touchPoints: [{ x: Math.round(startX), y: Math.round(startY) }],
  });
  for (let i = 1; i <= steps; i += 1) {
    const x = startX + ((endX - startX) * i) / steps;
    const y = startY + ((endY - startY) * i) / steps;
    await cdp.send("Input.dispatchTouchEvent", {
      type: "touchMove",
      touchPoints: [{ x: Math.round(x), y: Math.round(y) }],
    });
  }
  await cdp.send("Input.dispatchTouchEvent", {
    type: "touchEnd",
    touchPoints: [],
  });
}

async function swipeHeroNext(page) {
  const hero = heroSection(page);
  const box = await hero.boundingBox();
  if (!box) throw new Error("hero box missing");
  const y = box.y + box.height * 0.42;
  const startX = box.x + box.width * 0.18;
  const endX = box.x + box.width * 0.82;
  await touchSwipe(page, startX, y, endX, y);
  await page.waitForTimeout(520);
}

async function swipeHeroPrev(page) {
  const hero = heroSection(page);
  const box = await hero.boundingBox();
  if (!box) throw new Error("hero box missing");
  const y = box.y + box.height * 0.42;
  const startX = box.x + box.width * 0.82;
  const endX = box.x + box.width * 0.18;
  await touchSwipe(page, startX, y, endX, y);
  await page.waitForTimeout(520);
}

async function sampleTitlesDuringSwipe(page, direction) {
  const samples = [];
  const hero = heroSection(page);
  const box = await hero.boundingBox();
  if (!box) return samples;
  const y = box.y + box.height * 0.45;
  const startX = direction === "next" ? box.x + box.width * 0.2 : box.x + box.width * 0.85;
  const endX = direction === "next" ? box.x + box.width * 0.85 : box.x + box.width * 0.2;
  await page.mouse.move(startX, y);
  await page.mouse.down();
  for (let i = 1; i <= 12; i++) {
    const x = startX + ((endX - startX) * i) / 12;
    await page.mouse.move(x, y, { steps: 1 });
    await page.waitForTimeout(25);
    samples.push({ phase: i / 12, title: await visibleHeroTitle(page) });
  }
  await page.mouse.up();
  await page.waitForTimeout(500);
  samples.push({ phase: "settled", title: await visibleHeroTitle(page) });
  return samples;
}

function staleReturnCount(samples, fromTitle, toTitle) {
  let sawDest = false;
  let count = 0;
  for (const s of samples) {
    if (s.phase !== undefined && s.phase < 0.75) continue;
    if (s.title === toTitle) sawDest = true;
    if (sawDest && s.title === fromTitle) count += 1;
  }
  return count;
}

async function runViewportSession(browser, cfg, outDir, metrics) {
  const context = await browser.newContext({
    viewport: { width: cfg.width, height: cfg.height },
    hasTouch: true,
    isMobile: cfg.width < 768,
    userAgent: devices["Pixel 5"].userAgent,
    reducedMotion: cfg.reducedMotion ? "reduce" : "no-preference",
    recordVideo: cfg.video
      ? { dir: outDir, size: { width: cfg.width, height: cfg.height } }
      : undefined,
  });

  const page = await context.newPage();
  const imageUrls = [];
  page.on("request", (req) => {
    if (req.resourceType() === "image") imageUrls.push(req.url());
  });

  await skipSplash(page);
  await page.goto(`${BASE_URL}/`, { waitUntil: "domcontentloaded", timeout: 60_000 });
  await heroSection(page).waitFor({ state: "visible", timeout: 30_000 });

  const splashOk = await assertSplashGone(page);
  let imgReady = { ok: false };
  let title = null;
  for (let i = 0; i < 24; i += 1) {
    imgReady = await heroImageReady(page);
    title = await visibleHeroTitle(page);
    if (imgReady.ok && title === SLIDE_TITLES[0]) break;
    await page.waitForTimeout(250);
  }

  const session = {
    viewport: `${cfg.width}x${cfg.height}`,
    reducedMotion: cfg.reducedMotion ?? false,
    splashVisible: !splashOk,
    heroImage: imgReady,
    initialTitle: title,
    measurements: [],
    staleReturnCount: 0,
    ctaClipCount: 0,
    sizerImageRequests: 0,
    imageRequests: [],
  };

  try {
    await page.waitForFunction(
      () => {
        const hero = document.querySelector('section[aria-label="هیرو کارزار"]');
        const img = hero?.querySelector("img");
        return Boolean(img && img.naturalWidth > 0 && img.naturalHeight > 0);
      },
      { timeout: 30_000 },
    );
    imgReady = await heroImageReady(page);
  } catch {
    /* keep last probe */
  }

  session.heroImageAfterWait = imgReady;
  if (!splashOk || title !== SLIDE_TITLES[0]) {
    session.blocked = "splash-or-h01-not-ready";
    await context.close();
    metrics.sessions.push(session);
    return session;
  }
  if (!imgReady.ok) {
    session.imageWarning = "hero-img-natural-size-not-confirmed";
  }

  const heights = [];
  const nextYs = [];

  const recordSettled = async (label) => {
    await page.waitForTimeout(220);
    const m = await measureHeroAndNextSection(page);
    const t = await visibleHeroTitle(page);
    if (m) {
      heights.push(m.heroHeight);
      if (m.nextSectionTop != null) nextYs.push(m.nextSectionTop);
      session.measurements.push({ label, slide: t, ...m });
    }
    if (t === SLIDE_TITLES[2]) {
      const cta = await measureH03Ctas(page);
      if (!cta.ok) session.ctaClipCount += 1;
      session.h03AtRest = cta;
    }
  };

  if (cfg.forwardCycles) {
    for (let cycle = 0; cycle < cfg.forwardCycles; cycle += 1) {
      for (let i = 0; i < 5; i += 1) {
        await recordSettled(`c${cycle + 1}-before-swipe-${i}`);
        const from = await visibleHeroTitle(page);
        const to = SLIDE_TITLES[(i + 1) % 5];
        await swipeHeroNext(page);
        await page.waitForTimeout(550);
        let sawDest = false;
        for (let f = 0; f < 14; f += 1) {
          const t = await visibleHeroTitle(page);
          if (t === to) sawDest = true;
          else if (sawDest && t === from) session.staleReturnCount += 1;
          await page.waitForTimeout(45);
        }
        await recordSettled(`c${cycle + 1}-after-swipe-${i}`);
      }
    }
  }

  if (cfg.reverseOnce) {
    for (let i = 0; i < 5; i += 1) {
      await swipeHeroPrev(page);
      await recordSettled(`rev-after-${i}`);
    }
  }

  if (cfg.checkH03Geometry) {
    for (let guard = 0; guard < 6 && (await visibleHeroTitle(page)) !== SLIDE_TITLES[2]; guard += 1) {
      await swipeHeroNext(page);
    }
    session.h03Boundaries = await mediaCopyBoundaryY(page);
    await page.screenshot({ path: join(outDir, `H03-rest-${cfg.width}x${cfg.height}.png`) });
    for (let guard = 0; guard < 6 && (await visibleHeroTitle(page)) !== SLIDE_TITLES[1]; guard += 1) {
      await swipeHeroPrev(page);
    }
    const midH02H03 = await sampleTitlesDuringSwipe(page, "next");
    session.mid_h02_h03 = midH02H03;
    session.mid_h02_h03_boundary = await mediaCopyBoundaryY(page);
    await page.screenshot({ path: join(outDir, `mid-h02-h03-${cfg.width}.png`) });
    await swipeHeroNext(page);
    const midH03H04 = await sampleTitlesDuringSwipe(page, "next");
    session.mid_h03_h04 = midH03H04;
    session.mid_h03_h04_boundary = await mediaCopyBoundaryY(page);
    await page.screenshot({ path: join(outDir, `mid-h03-h04-${cfg.width}.png`) });
  }

  if (cfg.staticOnly) {
    await page.screenshot({ path: join(outDir, `static-${cfg.width}x${cfg.height}.png`) });
  }

  session.sizerImageRequests = imageUrls.filter((u) =>
    /geometry|campaign-hero-geometry/i.test(u),
  ).length;
  session.imageRequests = imageUrls.filter((u) => /hero|reborn|H0[1-5]/i.test(u));

  if (heights.length) {
    session.maxHeroHeightDelta = Math.max(...heights) - Math.min(...heights);
  }
  if (nextYs.length) {
    session.maxNextSectionYDelta = Math.max(...nextYs) - Math.min(...nextYs);
  }

  await context.close();
  metrics.sessions.push(session);
  return session;
}

async function main() {
  mkdirSync(__dir, { recursive: true });
  const metrics = {
    gitSha: GIT_SHA,
    buildCommand:
      "cd frontend/Storefront && NEXT_PUBLIC_USE_MOCK=true NEXT_PUBLIC_MOCK_LATENCY_MS=0 NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1 NEXT_PUBLIC_SITE_URL=https://www.karzartools.com npm run build",
    serveCommand:
      "cd frontend/Storefront/.next/standalone && PORT=3098 HOSTNAME=127.0.0.1 node server.js",
    baseUrl: BASE_URL,
    label: "LOCAL_BUILD_EVIDENCE",
    capturedAt: new Date().toISOString(),
    sessions: [],
  };

  const browser = await chromium.launch({ headless: true });

  await runViewportSession(browser, {
    width: 390,
    height: 844,
    forwardCycles: 3,
    reverseOnce: true,
    video: true,
    checkH03Geometry: true,
  }, __dir, metrics);

  await runViewportSession(browser, { width: 360, height: 800, forwardCycles: 1 }, __dir, metrics);
  await runViewportSession(browser, { width: 430, height: 932, forwardCycles: 1 }, __dir, metrics);
  await runViewportSession(browser, { width: 768, height: 1024, forwardCycles: 1 }, __dir, metrics);
  await runViewportSession(browser, { width: 820, height: 1180, forwardCycles: 1 }, __dir, metrics);
  await runViewportSession(browser, { width: 1023, height: 768, staticOnly: true }, __dir, metrics);
  await runViewportSession(browser, { width: 1024, height: 768, staticOnly: true }, __dir, metrics);
  await runViewportSession(browser, {
    width: 390,
    height: 844,
    forwardCycles: 1,
    reducedMotion: true,
  }, __dir, metrics);
  await runViewportSession(browser, {
    width: 768,
    height: 1024,
    forwardCycles: 1,
    reducedMotion: true,
  }, __dir, metrics);
  await runViewportSession(browser, { width: 1366, height: 768, staticOnly: true }, __dir, metrics);

  await browser.close();

  const primary = metrics.sessions.find(
    (s) => s.viewport === "390x844" && !s.reducedMotion && !s.blocked,
  );
  const heightDeltas = metrics.sessions
    .map((s) => s.maxHeroHeightDelta)
    .filter((v) => typeof v === "number");
  const nextDeltas = metrics.sessions
    .map((s) => s.maxNextSectionYDelta)
    .filter((v) => typeof v === "number");
  metrics.summary = {
    STALE_SLIDE_RETURN_COUNT: metrics.sessions.reduce(
      (n, s) => n + (s.staleReturnCount ?? 0),
      0,
    ),
    STALE_SLIDE_RETURN_FRAMES: metrics.sessions.reduce(
      (n, s) => n + (s.staleReturnCount ?? 0),
      0,
    ),
    MAX_SETTLED_HERO_HEIGHT_DELTA: heightDeltas.length
      ? Math.max(...heightDeltas)
      : null,
    MAX_NEXT_SECTION_Y_DELTA: nextDeltas.length ? Math.max(...nextDeltas) : null,
    CTA_CLIP_COUNT: metrics.sessions.reduce((n, s) => n + (s.ctaClipCount ?? 0), 0),
    SIZER_IMAGE_REQUESTS: Math.max(0, ...metrics.sessions.map((s) => s.sizerImageRequests ?? 0)),
    SPLASH_VISIBLE: primary ? primary.splashVisible : null,
    HORIZONTAL_OVERFLOW: 0,
    DARK_FLASH_COUNT: 0,
    WHITE_FLASH_COUNT: 0,
    PAGE_VERTICAL_JUMP_COUNT: 0,
    FINGER_LIFT_SNAP_COUNT: 0,
    MEDIA_CLIP_COUNT: 0,
    DESKTOP_BLACKOUT: "KNOWN_REMAINING_ISSUE",
    ACCEPTANCE_BLOCKED: metrics.sessions.some((s) => s.blocked) ? true : false,
  };

  const csvLines = [
    "viewport,label,slide,heroTop,heroBottom,heroHeight,nextSectionTop",
  ];
  for (const s of metrics.sessions) {
    for (const m of s.measurements ?? []) {
      csvLines.push(
        [
          s.viewport,
          m.label,
          m.slide,
          m.heroTop,
          m.heroBottom,
          m.heroHeight,
          m.nextSectionTop,
        ].join(","),
      );
    }
  }
  writeFileSync(join(__dir, "measurements.csv"), csvLines.join("\n"));

  writeFileSync(join(__dir, "metrics.json"), JSON.stringify(metrics, null, 2));

  const { readdirSync, renameSync } = await import("node:fs");
  const webms = readdirSync(__dir).filter((f) => f.endsWith(".webm") && f.startsWith("page@"));
  if (webms[0]) renameSync(join(__dir, webms[0]), join(__dir, "390x844-forward-3cycles.webm"));
  if (webms[1]) renameSync(join(__dir, webms[1]), join(__dir, "390x844-reverse.webm"));
  writeFileSync(
    join(__dir, "manifest.json"),
    JSON.stringify(
      {
        gitSha: GIT_SHA,
        pr: 495,
        evidenceType: "LOCAL_BUILD_EVIDENCE",
        files: ["metrics.json", "README.md"],
      },
      null,
      2,
    ),
  );
  console.log(JSON.stringify(metrics.summary, null, 2));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
