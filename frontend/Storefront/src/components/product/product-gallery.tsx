"use client";

import { useState } from "react";
import Image from "next/image";
import { cn } from "@/lib/utils";
import type { ProductImage } from "@/types/product";

export function ProductGallery({
  images,
  alt,
}: {
  images: ProductImage[];
  alt: string;
}) {
  const list = images.length ? images : [];
  const [active, setActive] = useState(
    list.find((i) => i.is_primary)?.id ?? list[0]?.id ?? 0,
  );
  const current = list.find((i) => i.id === active) ?? list[0];

  if (!list.length) {
    return (
      <div className="grid aspect-square place-items-center rounded-xl bg-accent text-accent-foreground">
        <span className="text-3xl font-medium">{alt.slice(0, 2) || "ک"}</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col-reverse gap-4 sm:flex-row">
      {list.length > 1 && (
        <div className="flex gap-3 overflow-x-auto pb-1 no-scrollbar sm:flex-col sm:overflow-visible sm:pb-0">
          {list.map((img) => (
            <button
              key={img.id}
              type="button"
              onClick={() => setActive(img.id)}
              className={cn(
                "relative h-16 w-16 shrink-0 overflow-hidden rounded-lg bg-muted/40 shadow-soft transition-all",
                active === img.id ? "ring-2 ring-primary" : "opacity-70 hover:opacity-100",
              )}
            >
              <Image
                src={img.url}
                alt={alt}
                fill
                sizes="64px"
                className="object-contain p-1"
              />
            </button>
          ))}
        </div>
      )}
      <div className="relative aspect-square flex-1 overflow-hidden rounded-xl bg-muted/40">
        <Image
          src={current.url}
          alt={alt}
          fill
          sizes="(max-width: 768px) 100vw, 50vw"
          className="object-contain p-4"
          priority
        />
      </div>
    </div>
  );
}
