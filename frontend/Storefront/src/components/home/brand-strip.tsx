"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { useBrands } from "@/features/catalog/queries";
import { Skeleton } from "@/components/ui/skeleton";

export function BrandStrip() {
  const { data, isLoading } = useBrands();

  if (isLoading) {
    return (
      <div className="flex flex-wrap gap-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-40 rounded-2xl" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      {data?.map((brand, i) => (
        <motion.div
          key={brand.id}
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.35, delay: i * 0.05 }}
        >
          <Link
            href={`/catalog?brand=${brand.id}`}
            className="flex h-16 flex-col items-center justify-center rounded-2xl bg-card shadow-soft transition-shadow hover:shadow-card"
          >
            <span className="text-base font-bold text-foreground">{brand.name}</span>
            {brand.country && (
              <span className="text-xs text-muted-foreground">{brand.country}</span>
            )}
          </Link>
        </motion.div>
      ))}
    </div>
  );
}
