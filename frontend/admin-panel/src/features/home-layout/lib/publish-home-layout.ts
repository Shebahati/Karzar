import {
  normalizeHomeLayoutPack,
  type HomeLayoutPack,
} from "@/entities/home-layout";

export async function publishHomeLayoutPack(pack: HomeLayoutPack): Promise<{
  fileOk: boolean;
  publishedAt?: string | null;
  detail?: string;
  pack?: HomeLayoutPack;
}> {
  const payload: HomeLayoutPack = {
    version: 1,
    publishedAt: pack.publishedAt || new Date().toISOString(),
    sections: Array.isArray(pack.sections) ? pack.sections : [],
  };

  const fileRes = await fetch("/api/home-layout/publish", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!fileRes.ok) {
    let detail = `file_publish_${fileRes.status}`;
    try {
      const err = (await fileRes.json()) as {
        error?: string;
        issues?: { message: string }[];
      };
      if (err.issues?.length) {
        detail = err.issues.map((i) => i.message).join("؛ ");
      } else if (err.error) {
        detail = err.error;
      }
    } catch {
      /* keep status detail */
    }
    return { fileOk: false, detail };
  }

  try {
    const data = (await fileRes.json()) as {
      publishedAt?: string;
    };
    const refreshed = normalizeHomeLayoutPack({
      ...payload,
      publishedAt: data.publishedAt ?? payload.publishedAt,
    });
    return {
      fileOk: true,
      publishedAt: refreshed.publishedAt,
      pack: refreshed,
    };
  } catch {
    return { fileOk: true, pack: payload };
  }
}

export async function loadHomeLayoutPack(): Promise<HomeLayoutPack> {
  try {
    const res = await fetch("/api/home-layout/publish", { cache: "no-store" });
    if (!res.ok) return normalizeHomeLayoutPack(null);
    return normalizeHomeLayoutPack(await res.json());
  } catch {
    return normalizeHomeLayoutPack(null);
  }
}
