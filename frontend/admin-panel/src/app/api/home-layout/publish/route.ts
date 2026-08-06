import { promises as fs } from "fs";
import path from "path";
import { NextResponse } from "next/server";

import {
  normalizeHomeLayoutPack,
  validateHomeLayoutPack,
  type HomeLayoutPack,
} from "@/entities/home-layout";

export const runtime = "nodejs";

function resolveWriteTargets(): string[] {
  const adminPublic = path.join(process.cwd(), "public", "home-layout.json");
  const targets = [adminPublic];

  const storefrontPublic = path.resolve(
    process.cwd(),
    "..",
    "Storefront",
    "public",
    "home-layout.json",
  );
  targets.push(storefrontPublic);

  return targets;
}

export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ ok: false, error: "invalid_json" }, { status: 400 });
  }

  const pack = normalizeHomeLayoutPack(body);
  const issues = validateHomeLayoutPack(pack);
  if (issues.length) {
    return NextResponse.json(
      { ok: false, error: "invalid_pack", issues },
      { status: 400 },
    );
  }

  const published: HomeLayoutPack = {
    ...pack,
    publishedAt: new Date().toISOString(),
  };

  const payload = JSON.stringify(published, null, 2);
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
    publishedAt: published.publishedAt,
    sectionCount: published.sections.length,
    enabledCount: published.sections.filter((s) => s.enabled).length,
    written,
    failed,
  });
}

export async function GET() {
  const target = path.join(process.cwd(), "public", "home-layout.json");
  try {
    const raw = await fs.readFile(target, "utf8");
    return NextResponse.json(normalizeHomeLayoutPack(JSON.parse(raw)));
  } catch {
    return NextResponse.json(normalizeHomeLayoutPack(null));
  }
}
