import type { KB001EdgeType, KnowledgeEdgeStatus, KnowledgeNodeType } from "@/types/knowledge";

export const EDGE_TYPE_LABELS: Record<KB001EdgeType, string> = {
  PRODUCT_BELONGS_TO_CATEGORY: "محصول ← دسته",
  PRODUCT_BRANDED_AS: "محصول ← برند",
  ARTICLE_EXPLAINS_PRODUCT: "مقاله ← محصول",
};

export const EDGE_STATUS_LABELS: Record<KnowledgeEdgeStatus, string> = {
  asserted: "اعلام‌شده",
  published: "منتشر",
  rejected: "ردشده",
  deprecated: "منسوخ",
};

export const NODE_TYPE_LABELS: Record<KnowledgeNodeType, string> = {
  product: "محصول",
  category: "دسته",
  brand: "برند",
  article: "مقاله",
};

export function edgeTypeLabel(edgeType: KB001EdgeType): string {
  return EDGE_TYPE_LABELS[edgeType] ?? edgeType;
}

export function edgeStatusLabel(status: KnowledgeEdgeStatus): string {
  return EDGE_STATUS_LABELS[status] ?? status;
}

export function nodeTypeLabel(nodeType: KnowledgeNodeType): string {
  return NODE_TYPE_LABELS[nodeType] ?? nodeType;
}

export function formatNodeRef(nodeType: KnowledgeNodeType, nodeId: number): string {
  return `${nodeTypeLabel(nodeType)} #${nodeId}`;
}
