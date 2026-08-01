/** Mirrors OpenAPI Knowledge schemas — KB-001 wave-1 freeze (three edge types). */

export type KB001EdgeType =
  | "PRODUCT_BELONGS_TO_CATEGORY"
  | "PRODUCT_BRANDED_AS"
  | "ARTICLE_EXPLAINS_PRODUCT";

export type KnowledgeEdgeStatus = "asserted" | "published" | "rejected" | "deprecated";

export type KnowledgeNodeType = "product" | "category" | "brand" | "article";

export interface KnowledgeEdge {
  id: number;
  edge_type: KB001EdgeType;
  from_node_type: KnowledgeNodeType;
  from_node_id: number;
  to_node_type: KnowledgeNodeType;
  to_node_id: number;
  status: KnowledgeEdgeStatus;
  source_kind: string;
  source_ref: string | null;
  recorded_at: string;
  recorder: string;
  confidence: string | null;
  attributes: Record<string, unknown>;
}

export interface KnowledgeEdgeListResponse {
  items: KnowledgeEdge[];
  total: number;
}

export interface ProductNeighborhood {
  product_id: number;
  belongs_to_category: KnowledgeEdge | null;
  branded_as: KnowledgeEdge | null;
  explained_by_articles: KnowledgeEdge[];
}

export interface KnowledgeEdgeListParams {
  edge_type?: KB001EdgeType;
  from_type?: KnowledgeNodeType;
  from_id?: number;
  to_type?: KnowledgeNodeType;
  to_id?: number;
  status?: KnowledgeEdgeStatus;
  skip?: number;
  limit?: number;
}
