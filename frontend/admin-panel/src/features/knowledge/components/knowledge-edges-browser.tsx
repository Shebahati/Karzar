"use client";

import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  EDGE_TYPE_LABELS,
  edgeStatusLabel,
  edgeTypeLabel,
  formatNodeRef,
} from "@/features/knowledge/edge-labels";
import { useKnowledgeEdges } from "@/features/knowledge/queries";
import type { KB001EdgeType } from "@/types/knowledge";

type EdgeFilter = "all" | KB001EdgeType;

/** Read-only list — GET /knowledge/edges (KB-001 freeze types only). */
export function KnowledgeEdgesBrowser() {
  const [filter, setFilter] = useState<EdgeFilter>("all");
  const params =
    filter === "all"
      ? { limit: 50 }
      : { edge_type: filter, limit: 50 };
  const { data, isPending, isError } = useKnowledgeEdges(params);
  const items = data?.items ?? [];

  return (
    <Card className="border-transparent shadow-card">
      <CardHeader className="flex-row flex-wrap items-center justify-between gap-3">
        <CardTitle className="text-[#4F4F4F]">یال‌های پروجکت‌شده</CardTitle>
        <Select value={filter} onValueChange={(v) => setFilter(v as EdgeFilter)}>
          <SelectTrigger className="w-[220px]">
            <SelectValue placeholder="نوع یال" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">همه انواع</SelectItem>
            {(Object.keys(EDGE_TYPE_LABELS) as KB001EdgeType[]).map((key) => (
              <SelectItem key={key} value={key}>
                {EDGE_TYPE_LABELS[key]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </CardHeader>
      <CardContent>
        {isPending ? (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        ) : isError ? (
          <p className="py-8 text-center text-sm text-muted-foreground">
            دریافت فهرست یال‌ها ناموفق بود.
          </p>
        ) : items.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">
            یالی یافت نشد. روی استک محلی پس از{" "}
            <span className="tnum font-bold">alembic upgrade</span> و{" "}
            <span className="font-bold">projections/sync</span> داده ظاهر می‌شود.
          </p>
        ) : (
          <>
            <p className="mb-3 text-xs text-muted-foreground tnum">
              نمایش {items.length} از {data?.total ?? items.length}
            </p>
            <ul className="divide-y divide-border">
              {items.map((edge) => (
                <li key={edge.id} className="flex flex-col gap-1.5 py-3 text-sm">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <Badge variant="outline">{edgeTypeLabel(edge.edge_type)}</Badge>
                    <Badge variant="neutral">{edgeStatusLabel(edge.status)}</Badge>
                  </div>
                  <p className="tnum text-foreground">
                    {formatNodeRef(edge.from_node_type, edge.from_node_id)}
                    {" → "}
                    <span className="font-bold">
                      {formatNodeRef(edge.to_node_type, edge.to_node_id)}
                    </span>
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {edge.source_kind}
                    {edge.source_ref ? ` · ${edge.source_ref}` : ""}
                    {" · "}
                    {new Date(edge.recorded_at).toLocaleString("fa-IR")}
                  </p>
                </li>
              ))}
            </ul>
          </>
        )}
      </CardContent>
    </Card>
  );
}
