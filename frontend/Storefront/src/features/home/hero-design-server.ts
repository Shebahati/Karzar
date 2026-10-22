import "server-only";
import { promises as fs } from "node:fs";
import path from "node:path";
import { parseDesignedHeroPack } from "@/features/home/hero-design";
import type { DesignedHeroPack } from "@/types/hero-design";

export type PublishedHeroDesignRead = {
  pack: DesignedHeroPack | null;
  loadedAtMs: number | null;
};

export type HeroDesignPackApiFetchResult = {
  ok: boolean;
  status: number;
  notModified?: boolean;
  etag?: string;
  revisionId?: string;
  pack?: DesignedHeroPack | null;
};

type StorefrontHeroDesignApiBody = {
  revision_id?: string;
  etag?: string;
  pack?: unknown;
};

let lastStorefrontHeroEtag: string | undefined;

function normalizeEtag(value: string | null | undefined): string | undefined {
  if (!value) return undefined;
  return value.replace(/^"|"$/g, "");
}

function resolveHeroDesignApiBaseUrl(): string {
  const raw =
    process.env.HERO_DESIGN_API_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "https://api.karzartools.com/api/v1";
  return raw.replace(/\/$/, "");
}

/** Revision-aware read against FastAPI `GET /storefront/hero-design`. */
export async function fetchHeroDesignPackFromApi(
  baseUrl: string,
  etag?: string,
): Promise<HeroDesignPackApiFetchResult> {
  const url = `${baseUrl.replace(/\/$/, "")}/storefront/hero-design`;
  const headers: HeadersInit = {};
  const ifNoneMatch = normalizeEtag(etag);
  if (ifNoneMatch) {
    headers["If-None-Match"] = `"${ifNoneMatch}"`;
  }

  const response = await fetch(url, {
    headers,
    next: { revalidate: 60 },
  });

  const responseEtag = normalizeEtag(response.headers.get("etag"));

  if (response.status === 304) {
    return {
      ok: true,
      status: 304,
      notModified: true,
      etag: responseEtag ?? ifNoneMatch,
    };
  }

  if (!response.ok) {
    return { ok: false, status: response.status };
  }

  const body = (await response.json()) as StorefrontHeroDesignApiBody;
  const pack = parseDesignedHeroPack(body.pack ?? body);
  const mergedEtag = responseEtag ?? normalizeEtag(body.etag);

  return {
    ok: true,
    status: response.status,
    etag: mergedEtag,
    revisionId: body.revision_id,
    pack,
  };
}

async function readPublishedHeroDesignPackFromFile(): Promise<PublishedHeroDesignRead> {
  const loadedAtMs = Date.now();
  try {
    const filePath = path.join(process.cwd(), "public", "hero-design.json");
    const raw = await fs.readFile(filePath, "utf8");
    const pack = parseDesignedHeroPack(JSON.parse(raw) as unknown);
    return { pack, loadedAtMs: pack ? loadedAtMs : null };
  } catch {
    return { pack: null, loadedAtMs: null };
  }
}

/** Read runtime-published hero pack from the Storefront public directory. */
export async function readPublishedHeroDesignPack(): Promise<PublishedHeroDesignRead> {
  if (process.env.HERO_STOREFRONT_API_READ !== "1") {
    return readPublishedHeroDesignPackFromFile();
  }

  const apiResult = await fetchHeroDesignPackFromApi(
    resolveHeroDesignApiBaseUrl(),
    lastStorefrontHeroEtag,
  );

  if (apiResult.notModified) {
    return readPublishedHeroDesignPackFromFile();
  }

  if (apiResult.ok && apiResult.pack) {
    if (apiResult.etag) {
      lastStorefrontHeroEtag = apiResult.etag;
    }
    return { pack: apiResult.pack, loadedAtMs: Date.now() };
  }

  return readPublishedHeroDesignPackFromFile();
}
