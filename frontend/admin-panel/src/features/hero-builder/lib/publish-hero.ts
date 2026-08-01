import type { PublishedHeroPack } from "@/entities/hero";
import { cmsService } from "@/services/cms";

function primaryCta(config: PublishedHeroPack["slides"][number]["config"]) {
  const btn = config.buttons[0];
  return {
    cta_label: btn?.label ?? "مشاهده",
    cta_href: btn?.action?.type === "href" ? btn.action.value : "/catalog",
  };
}

function imageOf(config: PublishedHeroPack["slides"][number]["config"]) {
  if (config.background.mode === "image" && config.background.imageUrl) {
    return config.background.imageUrl;
  }
  return "/images/hero/karzar-metrology-lab.jpg";
}

/** Map design pack → CMS hero-slides so the live API-backed hero also updates. */
export async function syncPackToCmsSlides(pack: PublishedHeroPack): Promise<{
  created: number;
  updated: number;
}> {
  const existing = await cmsService.listHeroSlides({ limit: 100 });
  const current = existing.data ?? [];
  const byId = new Map(current.map((s) => [s.id, s]));

  let created = 0;
  let updated = 0;

  for (const slide of pack.slides) {
    const cta = primaryCta(slide.config);
    const payload = {
      title: slide.config.typography.title || slide.name,
      subtitle: slide.config.typography.subtitle || null,
      cta_label: cta.cta_label,
      cta_href: cta.cta_href,
      image: imageOf(slide.config),
      accent: "#D02327",
      sort_order: slide.sortOrder,
      is_active: slide.isActive,
    };

    const linked =
      typeof (slide as { cmsId?: number }).cmsId === "number"
        ? byId.get((slide as { cmsId?: number }).cmsId!)
        : undefined;

    const matchByTitle = current.find((s) => s.title === payload.title);

    if (linked) {
      await cmsService.updateHeroSlide(linked.id, payload);
      updated += 1;
    } else if (matchByTitle) {
      await cmsService.updateHeroSlide(matchByTitle.id, payload);
      updated += 1;
    } else {
      await cmsService.createHeroSlide(payload);
      created += 1;
    }
  }

  // Deactivate CMS slides that are no longer in the published pack (best-effort).
  const publishedTitles = new Set(
    pack.slides.map((s) => s.config.typography.title || s.name),
  );
  for (const cmsSlide of current) {
    if (!publishedTitles.has(cmsSlide.title) && cmsSlide.is_active) {
      await cmsService.updateHeroSlide(cmsSlide.id, { is_active: false });
      updated += 1;
    }
  }

  return { created, updated };
}

export async function publishHeroPack(pack: PublishedHeroPack): Promise<{
  fileOk: boolean;
  cms?: { created: number; updated: number };
  detail?: string;
}> {
  // Always send categoryDock explicitly — older clients dropped it and wiped the storefront dock.
  const payload: PublishedHeroPack = {
    version: 1,
    publishedAt: pack.publishedAt || new Date().toISOString(),
    slides: Array.isArray(pack.slides) ? pack.slides : [],
    categoryDock: {
      categories: Array.isArray(pack.categoryDock?.categories)
        ? pack.categoryDock.categories
        : [],
    },
    ...(pack.mobilePreset ? { mobilePreset: pack.mobilePreset } : {}),
  };

  const fileRes = await fetch("/api/hero-design/publish", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const fileOk = fileRes.ok;
  let detail: string | undefined;
  if (!fileOk) {
    try {
      const err = (await fileRes.json()) as { error?: string };
      detail = err.error ?? `file_publish_${fileRes.status}`;
    } catch {
      detail = `file_publish_${fileRes.status}`;
    }
  }

  let cms: { created: number; updated: number } | undefined;
  try {
    cms = await syncPackToCmsSlides(pack);
  } catch (err) {
    const cmsMsg = `cms_sync_failed: ${err instanceof Error ? err.message : "unknown"}`;
    detail = detail ? `${detail}; ${cmsMsg}` : cmsMsg;
  }

  return { fileOk, cms, detail };
}
