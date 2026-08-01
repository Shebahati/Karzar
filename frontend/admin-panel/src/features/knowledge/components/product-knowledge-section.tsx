"use client";

import Link from "next/link";
import { Category } from "react-iconly";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  edgeStatusLabel,
  edgeTypeLabel,
  formatNodeRef,
} from "@/features/knowledge/edge-labels";
import { useProductNeighborhood } from "@/features/knowledge/queries";
import type { KnowledgeEdge } from "@/types/knowledge";

function LinkedRef({ href, children }: { href?: string | null; children: string }) {
  if (!href) return <span className="font-bold">{children}</span>;
  return (
    <Link href={href} className="font-bold text-accent underline-offset-2 hover:underline">
      {children}
    </Link>
  );
}

function EdgeRow({
  label,
  edge,
  emptyText,
  primaryHref,
}: {
  label: string;
  edge: KnowledgeEdge | null | undefined;
  emptyText: string;
  primaryHref?: string | null;
}) {
  if (!edge) {
    return (
      <li className="flex flex-col gap-1 py-3 text-sm">
        <span className="font-bold text-[#4F4F4F]">{label}</span>
        <span className="text-muted-foreground">{emptyText}</span>
      </li>
    );
  }

  const isArticleEdge = edge.edge_type === "ARTICLE_EXPLAINS_PRODUCT";
  const primary = isArticleEdge
    ? formatNodeRef(edge.from_node_type, edge.from_node_id)
    : formatNodeRef(edge.to_node_type, edge.to_node_id);

  return (
    <li className="flex flex-col gap-1.5 py-3 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-bold text-[#4F4F4F]">{label}</span>
        <Badge variant="outline">{edgeStatusLabel(edge.status)}</Badge>
      </div>
      <p className="tnum text-foreground">
        <LinkedRef href={primaryHref}>{primary}</LinkedRef>
        {isArticleEdge ? (
          <span className="text-muted-foreground">{" → این محصول"}</span>
        ) : null}
      </p>
      <p className="text-xs text-muted-foreground">
        {edgeTypeLabel(edge.edge_type)}
        {edge.source_kind ? ` · ${edge.source_kind}` : ""}
        {edge.source_ref ? ` · ${edge.source_ref}` : ""}
      </p>
    </li>
  );
}

/** Read-only KB-001 neighborhood — GET /knowledge/products/{id}/neighborhood. */
export function ProductKnowledgeSection({ productId }: { productId: number }) {
  const { data, isPending, isError } = useProductNeighborhood(productId, productId > 0);

  return (
    <Card className="border-transparent shadow-card">
      <CardHeader className="flex-row flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Category set="bulk" size={22} primaryColor="#C22026" />
          <CardTitle className="text-[#4F4F4F]">گراف دانش (فقط خواندنی)</CardTitle>
        </div>
        <Badge variant="neutral">KB-001</Badge>
      </CardHeader>
      <CardContent>
        <p className="mb-3 text-xs leading-6 text-muted-foreground">
          یال‌های پروجکت‌شده از دسته‌بندی، برند و مقالات مرتبط. ویرایش Facts یا طبقه‌بندی دانش در
          این نسخه فعال نیست.
        </p>
        {isPending ? (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        ) : isError ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            دریافت همسایگی دانش ناموفق بود. اگر migration/sync اجرا نشده، یالی وجود ندارد.
          </p>
        ) : (
          <ul className="divide-y divide-border">
            <EdgeRow
              label="دستهٔ تجاری"
              edge={data?.belongs_to_category}
              emptyText="یال دسته‌بندی ثبت نشده است."
              primaryHref={data?.belongs_to_category ? "/catalog/categories" : null}
            />
            <EdgeRow
              label="برند"
              edge={data?.branded_as}
              emptyText="یال برند ثبت نشده است."
              primaryHref={data?.branded_as ? "/catalog/categories" : null}
            />
            {(data?.explained_by_articles?.length ?? 0) === 0 ? (
              <EdgeRow
                label="مقالات توضیح‌دهنده"
                edge={null}
                emptyText="مقاله‌ای این محصول را توضیح نمی‌دهد."
              />
            ) : (
              data!.explained_by_articles.map((edge) => (
                <EdgeRow
                  key={edge.id}
                  label="مقاله توضیح‌دهنده"
                  edge={edge}
                  emptyText=""
                  primaryHref="/cms/articles"
                />
              ))
            )}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
