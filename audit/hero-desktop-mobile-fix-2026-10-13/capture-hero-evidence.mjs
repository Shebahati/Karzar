/**
 * Heroes Reborn 5 desktop + mobile fix evidence (post #481 / #490).
 * Prefer production build: `npm run build && npm run start` in frontend/Storefront.
 *
 *   BASE_URL=http://127.0.0.1:3000 node audit/hero-desktop-mobile-fix-2026-10-13/capture-hero-evidence.mjs
 */
import { createRequire } from "node:module";
import { execSync } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(
  path.join(path.dirname(fileURLToPath(import.meta.url)), "../../frontend/Storefront/package.json"),
);
const { chromium, devices } = require("@playwright/test");

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT = __dirname;
const BASE_URL = process.env.BASE_URL ?? "http://127.0.0.1:3000";
const MOTION = process.env.HERO_MOTION ?? "no-preference";

let commitSha = "unknown";
try {
  commitSha = execSync("git rev-parse HEAD", { encoding: "utf8" }).trim();
} catch {
  /* optional */
}

const VIEWPORTS = [
  { id: "1920x1080", width: 1920, height: 1080, mobile: false, touchSwipe: false },
  { id: "1366x768", width: 1366, height: 768, mobile: false, touchSwipe: false },
  /** Compact layout but not phone strip — arrows, not drag strip. */
  { id: "768x1024", width: 768, height: 1024, mobile: false, touchSwipe: false },
  { id: "390x844", width: 390, height: 844, mobile: true, touchSwipe: true },
];

const SLIDES = [
  {
    index: 0,
    title: "تخفیف‌های ویژه‌ی کارزار",
    minCtas: 1,
  },
  {
    index: 1,
    title: "ابزار اندازه‌گیری",
    minCtas: 1,
  },
  {
    index: 2,
    title: "اینسرت و ابزارهای اینسرتی",
    minCtas: 2,
    ctaLabels: ["مشاهده اینسرت‌ها", "مشاهده ابزارهای اینسرتی"],
  },
  {
    index: 3,
    title: "فرز انگشتی",
    minCtas: 1,
  },
  {
    index: 4,
    title: "دستگاه‌های صنعتی",
    minCtas: 1,
  },
];

const TRANSITION_VIEWPORTS = new Set(["390x844", "768x1024"]);

function fail(message) {
  throw new Error(message);
}

async function readVisibleHeroTitle(page) {
  return page.evaluate(() => {
    const section = document.querySelector('section[aria-label="هیرو کارزار"]');
    if (!section) return "";
    const headings = section.querySelectorAll(
      '[data-testid="campaign-hero-compact"] h1, [data-testid="campaign-hero-compact"] h2, [data-testid="campaign-hero-fullbleed"] h1, [data-testid="campaign-hero-fullbleed"] h2',
    );
    for (const el of headings) {
      const root = el.closest('[data-testid="campaign-hero-compact"], [data-testid="campaign-hero-fullbleed"]');
      if (!root) continue;
      if (root.closest(".invisible")) continue;
      let node = root;
      while (node && node !== section) {
        if (node.getAttribute?.("aria-hidden") === "true") break;
        const style = window.getComputedStyle(node);
        if (style.opacity === "0" || style.visibility === "hidden" || style.display === "none") break;
        node = node.parentElement;
      }
      if (node && node !== section) continue;
      const rect = el.getBoundingClientRect();
      if (rect.width < 8 || rect.height < 8) continue;
      return el.textContent?.trim() ?? "";
    }
    return "";
  });
}

async function waitForSlideTitle(page, title, vpId) {
  const started = Date.now();
  while (Date.now() - started < 45_000) {
    const current = await readVisibleHeroTitle(page);
    if (current === title) return;
    await page.waitForTimeout(150);
  }
  fail(`[${vpId}] timed out waiting for slide title "${title}"`);
}

async function waitHeroSettled(page) {
  const hero = page.locator('section[aria-label="هیرو کارزار"]');
  await hero.waitFor({ state: "visible", timeout: 60_000 });
  await page.waitForFunction(
    () => {
      const section = document.querySelector('section[aria-label="هیرو کارزار"]');
      const rect = section?.getBoundingClientRect();
      return rect && rect.height >= 260;
    },
    undefined,
    { timeout: 60_000 },
  );
  await page.waitForTimeout(400);
}

async function assertSlide(page, slideSpec, vpId) {
  const hero = page.locator('section[aria-label="هیرو کارزار"]');
  const title = await readVisibleHeroTitle(page);
  if (title !== slideSpec.title) {
    fail(
      `[${vpId}] slide ${slideSpec.index + 1}: expected title "${slideSpec.title}", got "${title}"`,
    );
  }

  const box = await hero.boundingBox();
  if (!box || box.height < 280) {
    fail(`[${vpId}] slide ${slideSpec.index + 1}: hero height collapsed (${box?.height ?? 0}px)`);
  }

  const ctas = hero.locator("a").filter({ hasText: /مشاهده/ });
  const ctaCount = await ctas.count();
  if (ctaCount < slideSpec.minCtas) {
    fail(
      `[${vpId}] slide ${slideSpec.index + 1}: expected ≥${slideSpec.minCtas} CTAs, found ${ctaCount}`,
    );
  }
  if (slideSpec.ctaLabels) {
    for (const label of slideSpec.ctaLabels) {
      const link = hero.getByRole("link", { name: label });
      if (!(await link.count())) {
        fail(`[${vpId}] slide ${slideSpec.index + 1}: missing CTA "${label}"`);
      }
      const ctaBox = await link.first().boundingBox();
      if (!ctaBox || ctaBox.width < 8 || ctaBox.height < 8) {
        fail(`[${vpId}] slide ${slideSpec.index + 1}: CTA "${label}" not visible`);
      }
    }
  }

  const media = hero.locator('[data-testid="campaign-hero-compact-media"], img').first();
  if (await media.count()) {
    const mediaBox = await media.boundingBox();
    if (!mediaBox || mediaBox.height < 80) {
      fail(`[${vpId}] slide ${slideSpec.index + 1}: media band missing or collapsed`);
    }
  }
}

/** RTL carousel: drag finger/content toward physical right → next slide. */
async function swipeNextTouch(page, context, box) {
  const startX = box.x + box.width * 0.22;
  const endX = box.x + box.width * 0.78;
  const y = box.y + Math.min(box.height * 0.35, box.height - 48);
  const cdp = await context.newCDPSession(page);
  const point = (x) => [{ x: Math.round(x), y: Math.round(y), radiusX: 1, radiusY: 1 }];
  await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: point(startX) });
  for (let step = 1; step <= 16; step += 1) {
    const x = startX + ((endX - startX) * step) / 16;
    await cdp.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: point(x) });
  }
  await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
  await page.waitForTimeout(1200);
}

async function captureSlides(page, vp, context) {
  const shots = [];
  for (const slideSpec of SLIDES) {
    await waitHeroSettled(page);
    await assertSlide(page, slideSpec, vp.id);

    const file = path.join(OUT, "screenshots", `${vp.id}-slide-${slideSpec.index + 1}.png`);
    await page.screenshot({ path: file, fullPage: false });
    shots.push(file);

    if (slideSpec.index < SLIDES.length - 1) {
      const hero = page.locator('section[aria-label="هیرو کارزار"]');
      const box = await hero.boundingBox();
      if (!box) fail(`[${vp.id}] missing hero box before swipe`);

      const nextSpec = SLIDES[slideSpec.index + 1];
      if (vp.touchSwipe) {
        let advanced = false;
        for (let attempt = 0; attempt < 3 && !advanced; attempt += 1) {
          const swipeBox =
            (await hero.locator(".cursor-grab").first().boundingBox()) ?? box;
          await swipeNextTouch(page, context, swipeBox);
          const title = await readVisibleHeroTitle(page);
          if (title === nextSpec.title) {
            advanced = true;
            break;
          }
          await page.waitForTimeout(500);
        }
        if (!advanced) {
          fail(`[${vp.id}] touch swipe did not reach slide "${nextSpec.title}"`);
        }
      } else {
        await hero.getByRole("button", { name: "اسلاید بعدی" }).click();
        await waitForSlideTitle(page, nextSpec.title, vp.id);
      }
      await page.waitForTimeout(400);
    }
  }
  return shots;
}

async function assertDesktopAutoplayControl(page, vpId) {
  const control = page.getByTestId("hero-autoplay-control");
  if (!(await control.count())) {
    fail(`[${vpId}] missing desktop autoplay control`);
  }
  const box = await control.boundingBox();
  if (!box || box.width < 20) {
    fail(`[${vpId}] autoplay control not clickable`);
  }
}

async function main() {
  await mkdir(path.join(OUT, "screenshots"), { recursive: true });
  await mkdir(path.join(OUT, "videos"), { recursive: true });

  const browser = await chromium.launch();
  const meta = { commitSha, baseUrl: BASE_URL, motion: MOTION, viewports: [] };

  for (const vp of VIEWPORTS) {
    const contextOptions = {
      viewport: { width: vp.width, height: vp.height },
      reducedMotion: MOTION === "reduce" ? "reduce" : "no-preference",
      recordVideo: TRANSITION_VIEWPORTS.has(vp.id)
        ? { dir: path.join(OUT, "videos"), size: { width: vp.width, height: vp.height } }
        : undefined,
    };
    if (vp.mobile) {
      Object.assign(contextOptions, devices["Pixel 5"]);
      contextOptions.viewport = { width: vp.width, height: vp.height };
      contextOptions.hasTouch = true;
    }
    const context = await browser.newContext(contextOptions);
    const page = await context.newPage();
    await page.goto(`${BASE_URL}/`, { waitUntil: "domcontentloaded", timeout: 120_000 });

    if (!vp.mobile) {
      await waitHeroSettled(page);
      await assertDesktopAutoplayControl(page, vp.id);
    }

    const shots = await captureSlides(page, vp, context);

    const videos = [];
    const video = page.video();
    await context.close();
    if (video) {
      const videoPath = path.join(OUT, "videos", `${vp.id}-session.webm`);
      await video.saveAs(videoPath);
      videos.push(videoPath);
    }

    meta.viewports.push({ id: vp.id, touchSwipe: vp.touchSwipe, shots, videos });
  }

  const reduceMeta = [];
  for (const vp of VIEWPORTS.filter((v) => v.id === "768x1024" || v.id === "390x844")) {
    const contextOptions = {
      viewport: { width: vp.width, height: vp.height },
      reducedMotion: "reduce",
    };
    if (vp.mobile) {
      Object.assign(contextOptions, devices["Pixel 5"]);
      contextOptions.viewport = { width: vp.width, height: vp.height };
      contextOptions.hasTouch = true;
    }
    const context = await browser.newContext(contextOptions);
    const page = await context.newPage();
    await page.goto(`${BASE_URL}/`, { waitUntil: "domcontentloaded", timeout: 120_000 });
    await waitHeroSettled(page);
    await assertSlide(page, SLIDES[0], `${vp.id}-reduce`);
    const shot = path.join(OUT, "screenshots", `${vp.id}-reduce-slide-1.png`);
    await page.screenshot({ path: shot, fullPage: false });
    const hero = page.locator('section[aria-label="هیرو کارزار"]');
    const box = await hero.boundingBox();
    if (!box) fail(`[${vp.id}-reduce] missing hero box`);
    await hero.getByRole("button", { name: "اسلاید بعدی" }).click();
    await waitForSlideTitle(page, SLIDES[1].title, `${vp.id}-reduce`);
    await waitHeroSettled(page);
    await assertSlide(page, SLIDES[1], `${vp.id}-reduce`);
    const shot2 = path.join(OUT, "screenshots", `${vp.id}-reduce-slide-2.png`);
    await page.screenshot({ path: shot2, fullPage: false });
    reduceMeta.push({ id: vp.id, shots: [shot, shot2] });
    await context.close();
  }

  await writeFile(
    path.join(OUT, "manifest.json"),
    JSON.stringify(
      { ...meta, reducedMotion: reduceMeta, capturedAt: new Date().toISOString() },
      null,
      2,
    ),
  );
  await browser.close();
  console.log("Wrote evidence to", OUT);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
