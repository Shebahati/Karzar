import { apiClient, withStepUp } from "@/lib/api-client";
import { env } from "@/config/env";
import { getMockApi } from "@/lib/get-mock-api";
import type {
  Article,
  ArticleCreatePayload,
  ArticleListParams,
  ArticleListResponse,
  ArticleUpdatePayload,
  ContactSubmissionListParams,
  ContactSubmissionListResponse,
  HeroSlide,
  HeroSlideCreatePayload,
  HeroSlideListParams,
  HeroSlideListResponse,
  HeroSlideUpdatePayload,
  ProductCommentListParams,
  ProductCommentListResponse,
} from "@/types/cms";

export const cmsService = {
  async listArticles(params: ArticleListParams = {}): Promise<ArticleListResponse> {
    if (env.USE_MOCK) return (await getMockApi()).listArticles(params);
    const { data } = await apiClient.get<ArticleListResponse>("/cms/articles", { params });
    return data;
  },

  async createArticle(payload: ArticleCreatePayload): Promise<Article> {
    if (env.USE_MOCK) return (await getMockApi()).createArticle(payload);
    const { data } = await apiClient.post<Article>("/cms/articles", payload);
    return data;
  },

  async updateArticle(id: number, payload: ArticleUpdatePayload): Promise<Article> {
    if (env.USE_MOCK) return (await getMockApi()).updateArticle(id, payload);
    const { data } = await apiClient.put<Article>(`/cms/articles/${id}`, payload);
    return data;
  },

  async deleteArticle(id: number, stepUpToken: string): Promise<void> {
    if (env.USE_MOCK) return (await getMockApi()).deleteArticle(id, stepUpToken);
    await apiClient.delete(`/cms/articles/${id}`, withStepUp(stepUpToken));
  },

  async listHeroSlides(params: HeroSlideListParams = {}): Promise<HeroSlideListResponse> {
    if (env.USE_MOCK) return (await getMockApi()).listHeroSlides(params);
    // Live API returns { data: HeroSlide[] } without pagination meta.
    const { data } = await apiClient.get<{ data: HeroSlide[] }>("/cms/hero-slides");
    const rows = data.data ?? [];
    const skip = params.skip ?? 0;
    const limit = params.limit ?? (rows.length || 20);
    let filtered = rows;
    if (params.is_active !== undefined) {
      filtered = filtered.filter((s) => s.is_active === params.is_active);
    }
    return {
      data: filtered.slice(skip, skip + limit),
      meta: {
        total_count: filtered.length,
        skip,
        limit,
        has_next: skip + limit < filtered.length,
        has_prev: skip > 0,
      },
    };
  },

  async createHeroSlide(payload: HeroSlideCreatePayload): Promise<HeroSlide> {
    if (env.USE_MOCK) return (await getMockApi()).createHeroSlide(payload);
    const { data } = await apiClient.post<HeroSlide>("/cms/hero-slides", payload);
    return data;
  },

  async updateHeroSlide(id: number, payload: HeroSlideUpdatePayload): Promise<HeroSlide> {
    if (env.USE_MOCK) return (await getMockApi()).updateHeroSlide(id, payload);
    const { data } = await apiClient.put<HeroSlide>(`/cms/hero-slides/${id}`, payload);
    return data;
  },

  async deleteHeroSlide(id: number, stepUpToken: string): Promise<void> {
    if (env.USE_MOCK) return (await getMockApi()).deleteHeroSlide(id, stepUpToken);
    await apiClient.delete(`/cms/hero-slides/${id}`, withStepUp(stepUpToken));
  },

  async listProductComments(
    params: ProductCommentListParams = {},
  ): Promise<ProductCommentListResponse> {
    if (env.USE_MOCK) return (await getMockApi()).listProductComments(params);
    const { data } = await apiClient.get<ProductCommentListResponse>("/cms/product-comments", {
      params,
    });
    return data;
  },

  async deleteProductComment(id: number, stepUpToken: string): Promise<void> {
    if (env.USE_MOCK) return (await getMockApi()).deleteProductComment(id, stepUpToken);
    await apiClient.delete(`/cms/product-comments/${id}`, withStepUp(stepUpToken));
  },

  async listContactSubmissions(
    params: ContactSubmissionListParams = {},
  ): Promise<ContactSubmissionListResponse> {
    if (env.USE_MOCK) return (await getMockApi()).listContactSubmissions(params);
    const { data } = await apiClient.get<ContactSubmissionListResponse>(
      "/cms/contact-submissions",
      { params },
    );
    return data;
  },
};
