import { promises as fs } from "fs";
import path from "path";
import { NextResponse } from "next/server";

export const runtime = "nodejs";

type PublishedPack = {
  version: 1;
  publishedAt: string;
  slides: unknown[];
  categoryDock?: {
    categories: unknown[];
  };
  mobilePreset?: string;
};

function resolveWriteTargets(): string[] {
  const adminPublic = path.join(process.cwd(), "public", "hero-design.json");
  const targets = [adminPublic];

  // Sibling Storefront (local monorepo layout: karzar-frontend/{admin-panel,Storefront})
  const storefrontPublic = path.resolve(
    process.cwd(),
    "..",
    "Storefront",
    "public",
    "hero-design.json",
  );
  targets.push(storefrontPublic);

  return targets;
}

function normalizePack(body: PublishedPack): PublishedPack {
  const categories = Array.isArray(body.categoryDock?.categories)
    ? body.categoryDock!.categories
    : [];

  return {
    version: 1,
    publishedAt: body.publishedAt || new Date().toISOString(),
    slides: Array.isArray(body.slides) ? body.slides : [],
    categoryDock: { categories },
    ...(body.mobilePreset ? { mobilePreset: body.mobilePreset } : {}),
  };
}

export async function POST(request: Request) {
  let body: PublishedPack;
  try {
    body = (await request.json()) as PublishedPack;
  } catch {
    return NextResponse.json({ ok: false, error: "invalid_json" }, { status: 400 });
  }

  if (!body || body.version !== 1 || !Array.isArray(body.slides)) {
    return NextResponse.json({ ok: false, error: "invalid_pack" }, { status: 400 });
  }

  const pack = normalizePack(body);

  const payload = JSON.stringify(pack, null, 2);
  const written: string[] = [];
  const failed: string[] = [];

  for (const target of resolveWriteTargets()) {
    try {
      await fs.mkdir(path.dirname(target), { recursive: true });
      await fs.writeFile(target, payload, "utf8");
      written.push(target);
    } catch {
      failed.push(target);
    }
  }

  if (!written.length) {
    return NextResponse.json(
      { ok: false, error: "write_failed", failed },
      { status: 500 },
    );
  }

  return NextResponse.json({
    ok: true,
    publishedAt: pack.publishedAt,
    slideCount: pack.slides.length,
    dockCount: pack.categoryDock?.categories.length ?? 0,
    featuredCount:
      pack.categoryDock?.categories.filter(
        (c) =>
          c &&
          typeof c === "object" &&
          "featuredOrder" in c &&
          (c as { featuredOrder: unknown }).featuredOrder != null,
      ).length ?? 0,
    written,
    failed,
  });
}

export async function GET() {
  const target = path.join(process.cwd(), "public", "hero-design.json");
  try {
    const raw = await fs.readFile(target, "utf8");
    return NextResponse.json(JSON.parse(raw));
  } catch {
    return NextResponse.json({
      version: 1,
      publishedAt: null,
      slides: [],
      categoryDock: { categories: [] },
    });
  }
}
