"use client";

import Image from "next/image";
import Link from "next/link";
import { motion } from "framer-motion";
import { Calendar, TimeCircle } from "react-iconly";
import { Container } from "@/components/ui/container";
import { Skeleton } from "@/components/ui/skeleton";
import { useArticles } from "@/features/catalog/queries";
import { formatNumber } from "@/lib/utils";

function faDate(iso: string) {
  return new Date(iso).toLocaleDateString("fa-IR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export function BlogList() {
  const { data, isLoading } = useArticles();

  return (
    <div className="bg-hero-glow">
      <Container className="py-10 lg:py-16">
        <div className="mb-10 text-center">
          <span className="inline-block rounded-full bg-accent px-3 py-1 text-xs font-bold text-primary">
            مجله کارزار
          </span>
          <h1 className="mt-4 text-3xl font-bold text-foreground">
            دانش، راهنما و دنیای ابزار
          </h1>
          <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
            جدیدترین مقالات تخصصی برای انتخاب و نگهداری بهتر ابزارها
          </p>
        </div>

        {isLoading ? (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-80 rounded-2xl" />
            ))}
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {data?.map((article, i) => (
              <motion.article
                key={article.id}
                initial={{ opacity: 0, y: 28 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ duration: 0.45, delay: (i % 3) * 0.08 }}
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
                    <h2 className="line-clamp-2 text-base font-bold leading-7 text-foreground transition-colors group-hover:text-primary">
                      {article.title}
                    </h2>
                    <p className="mt-2 line-clamp-2 flex-1 text-sm leading-6 text-muted-foreground">
                      {article.excerpt}
                    </p>
                    <div className="mt-4 flex items-center justify-between text-xs text-muted-foreground">
                      <span className="flex items-center gap-1.5">
                        <Calendar size="small" set="light" />
                        {faDate(article.published_at)}
                      </span>
                      <span className="flex items-center gap-1.5">
                        <TimeCircle size="small" set="light" />
                        {formatNumber(article.reading_minutes)} دقیقه
                      </span>
                    </div>
                  </div>
                </Link>
              </motion.article>
            ))}
          </div>
        )}
      </Container>
    </div>
  );
}
