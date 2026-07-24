"use client";

import Image from "next/image";
import Link from "next/link";
import { motion } from "framer-motion";
import { TimeCircle } from "react-iconly";
import { useArticles } from "@/features/catalog/queries";
import { Skeleton } from "@/components/ui/skeleton";
import { formatNumber } from "@/lib/utils";

export function ArticlesSection() {
  const { data, isLoading } = useArticles();

  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-64 rounded-2xl" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid gap-5 sm:grid-cols-3">
      {data?.map((article, i) => (
        <motion.article
          key={article.id}
          initial={{ opacity: 0, y: 28 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-60px" }}
          transition={{ duration: 0.45, delay: i * 0.08 }}
        >
          <Link
            href={`/blog/${article.slug}`}
            className="group flex h-full flex-col overflow-hidden rounded-2xl bg-card shadow-soft transition-shadow hover:shadow-elevated"
          >
            <div className="relative aspect-[16/10] overflow-hidden">
              <Image
                src={article.cover_image}
                alt={article.title}
                fill
                sizes="(max-width: 768px) 100vw, 33vw"
                className="object-cover transition-transform duration-300 group-hover:scale-105"
              />
            </div>
            <div className="flex flex-1 flex-col p-5">
              <h3 className="line-clamp-2 text-base font-bold leading-7 text-foreground transition-colors group-hover:text-primary">
                {article.title}
              </h3>
              <p className="mt-2 line-clamp-2 flex-1 text-sm leading-6 text-muted-foreground">
                {article.excerpt}
              </p>
              <div className="mt-4 flex items-center gap-1.5 text-xs text-muted-foreground">
                <TimeCircle size="small" set="light" />
                {formatNumber(article.reading_minutes)} دقیقه مطالعه
              </div>
            </div>
          </Link>
        </motion.article>
      ))}
    </div>
  );
}
