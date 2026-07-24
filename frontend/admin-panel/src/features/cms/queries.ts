"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { cmsService } from "@/services/cms";
import type { ApiError } from "@/lib/api-client";
import type {
  Article,
  ArticleCreatePayload,
  ArticleListParams,
  ArticleUpdatePayload,
  ContactSubmissionListParams,
  HeroSlide,
  HeroSlideCreatePayload,
  HeroSlideListParams,
  HeroSlideUpdatePayload,
  ProductCommentListParams,
} from "@/types/cms";

/** Centralized, hierarchical query keys for safe cache invalidation. */
export const cmsKeys = {
  all: ["cms"] as const,
  articles: () => [...cmsKeys.all, "articles"] as const,
  articleList: (params: ArticleListParams) => [...cmsKeys.articles(), "list", params] as const,
  heroSlides: () => [...cmsKeys.all, "hero-slides"] as const,
  heroSlideList: (params: HeroSlideListParams) => [...cmsKeys.heroSlides(), "list", params] as const,
  comments: () => [...cmsKeys.all, "comments"] as const,
  commentList: (params: ProductCommentListParams) => [...cmsKeys.comments(), "list", params] as const,
  contacts: () => [...cmsKeys.all, "contacts"] as const,
  contactList: (params: ContactSubmissionListParams) => [...cmsKeys.contacts(), "list", params] as const,
};

/* -------------------------------------------------------------------------- */
/*  Articles                                                                 */
/* -------------------------------------------------------------------------- */

export function useArticles(params: ArticleListParams = {}) {
  return useQuery({
    queryKey: cmsKeys.articleList(params),
    queryFn: () => cmsService.listArticles(params),
    placeholderData: keepPreviousData,
  });
}

export function useCreateArticle() {
  const queryClient = useQueryClient();
  return useMutation<Article, ApiError, ArticleCreatePayload>({
    mutationFn: (payload) => cmsService.createArticle(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: cmsKeys.articles() });
    },
  });
}

export function useUpdateArticle() {
  const queryClient = useQueryClient();
  return useMutation<Article, ApiError, { id: number; payload: ArticleUpdatePayload }>({
    mutationFn: ({ id, payload }) => cmsService.updateArticle(id, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: cmsKeys.articles() });
    },
  });
}

export function useDeleteArticle() {
  const queryClient = useQueryClient();
  return useMutation<void, ApiError, { id: number; stepUpToken: string }>({
    mutationFn: ({ id, stepUpToken }) => cmsService.deleteArticle(id, stepUpToken),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: cmsKeys.articles() });
    },
  });
}

/* -------------------------------------------------------------------------- */
/*  Hero slides                                                              */
/* -------------------------------------------------------------------------- */

export function useHeroSlides(params: HeroSlideListParams = {}) {
  return useQuery({
    queryKey: cmsKeys.heroSlideList(params),
    queryFn: () => cmsService.listHeroSlides(params),
    placeholderData: keepPreviousData,
  });
}

export function useCreateHeroSlide() {
  const queryClient = useQueryClient();
  return useMutation<HeroSlide, ApiError, HeroSlideCreatePayload>({
    mutationFn: (payload) => cmsService.createHeroSlide(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: cmsKeys.heroSlides() });
    },
  });
}

export function useUpdateHeroSlide() {
  const queryClient = useQueryClient();
  return useMutation<HeroSlide, ApiError, { id: number; payload: HeroSlideUpdatePayload }>({
    mutationFn: ({ id, payload }) => cmsService.updateHeroSlide(id, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: cmsKeys.heroSlides() });
    },
  });
}

export function useDeleteHeroSlide() {
  const queryClient = useQueryClient();
  return useMutation<void, ApiError, { id: number; stepUpToken: string }>({
    mutationFn: ({ id, stepUpToken }) => cmsService.deleteHeroSlide(id, stepUpToken),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: cmsKeys.heroSlides() });
    },
  });
}

/* -------------------------------------------------------------------------- */
/*  Product comments                                                        */
/* -------------------------------------------------------------------------- */

export function useProductComments(params: ProductCommentListParams = {}) {
  return useQuery({
    queryKey: cmsKeys.commentList(params),
    queryFn: () => cmsService.listProductComments(params),
    placeholderData: keepPreviousData,
  });
}

export function useDeleteProductComment() {
  const queryClient = useQueryClient();
  return useMutation<void, ApiError, { id: number; stepUpToken: string }>({
    mutationFn: ({ id, stepUpToken }) => cmsService.deleteProductComment(id, stepUpToken),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: cmsKeys.comments() });
    },
  });
}

/* -------------------------------------------------------------------------- */
/*  Contact submissions                                                      */
/* -------------------------------------------------------------------------- */

export function useContactSubmissions(params: ContactSubmissionListParams = {}) {
  return useQuery({
    queryKey: cmsKeys.contactList(params),
    queryFn: () => cmsService.listContactSubmissions(params),
    placeholderData: keepPreviousData,
  });
}
