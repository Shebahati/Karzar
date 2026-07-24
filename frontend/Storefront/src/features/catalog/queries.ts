"use client";

import {
  keepPreviousData,
  useQuery,
  type UseQueryResult,
} from "@tanstack/react-query";
import { catalogService } from "@/services/catalog";
import { catalogKeys } from "@/features/catalog/keys";
import type { Brand, CategoryFlat, CategoryTreeNode } from "@/types/category";
import type { Article, BlogPost, HeroSlide, ProductComment } from "@/types/content";
import type {
  ProductDetail,
  ProductListParams,
  ProductListResponse,
  ProductSummary,
} from "@/types/product";

export { catalogKeys };

export function useCategoryTree(): UseQueryResult<CategoryTreeNode[]> {
  return useQuery({
    queryKey: catalogKeys.categoriesTree(),
    queryFn: () => catalogService.listCategoriesTree(),
    staleTime: 10 * 60 * 1000,
  });
}

export function useFlatCategories(): UseQueryResult<CategoryFlat[]> {
  return useQuery({
    queryKey: catalogKeys.categoriesFlat(),
    queryFn: () => catalogService.listCategoriesFlat(),
    staleTime: 10 * 60 * 1000,
  });
}

export function useBrands(): UseQueryResult<Brand[]> {
  return useQuery({
    queryKey: catalogKeys.brands(),
    queryFn: () => catalogService.listBrands(),
    staleTime: 10 * 60 * 1000,
  });
}

export function useProducts(
  params: ProductListParams,
): UseQueryResult<ProductListResponse> {
  return useQuery({
    queryKey: catalogKeys.products(params),
    queryFn: () => catalogService.listProducts(params),
    placeholderData: keepPreviousData,
  });
}

export function useProduct(id: number): UseQueryResult<ProductDetail> {
  return useQuery({
    queryKey: catalogKeys.product(id),
    queryFn: () => catalogService.getProduct(id),
    enabled: Number.isFinite(id) && id > 0,
  });
}

export function useRelatedProducts(
  id: number,
  enabled = true,
): UseQueryResult<ProductSummary[]> {
  return useQuery({
    queryKey: catalogKeys.related(id),
    queryFn: () => catalogService.getRelatedProducts(id),
    enabled: enabled && Number.isFinite(id) && id > 0,
  });
}

export function useComments(
  id: number,
  enabled = true,
): UseQueryResult<ProductComment[]> {
  return useQuery({
    queryKey: catalogKeys.comments(id),
    queryFn: () => catalogService.listComments(id),
    enabled: enabled && Number.isFinite(id) && id > 0,
  });
}

export function useArticles(): UseQueryResult<Article[]> {
  return useQuery({
    queryKey: catalogKeys.articles(),
    queryFn: () => catalogService.listArticles(),
    staleTime: 10 * 60 * 1000,
  });
}

export function useArticle(slug: string): UseQueryResult<BlogPost> {
  return useQuery({
    queryKey: catalogKeys.article(slug),
    queryFn: () => catalogService.getArticle(slug),
    enabled: Boolean(slug),
    staleTime: 10 * 60 * 1000,
  });
}

export function useProductsByIds(ids: number[]): UseQueryResult<ProductSummary[]> {
  const normalized = [...ids].filter((id) => Number.isFinite(id) && id > 0).sort((a, b) => a - b);
  return useQuery({
    queryKey: catalogKeys.productsByIds(normalized),
    queryFn: () => catalogService.getProductsByIds(normalized),
    enabled: normalized.length > 0,
    staleTime: 5 * 60 * 1000,
  });
}

export function useHeroSlides(): UseQueryResult<HeroSlide[]> {
  return useQuery({
    queryKey: catalogKeys.hero(),
    queryFn: () => catalogService.listHeroSlides(),
    staleTime: 10 * 60 * 1000,
  });
}

export function useSpecFilterOptions(categoryId: number) {
  return useQuery({
    queryKey: catalogKeys.specFilterOptions(categoryId),
    queryFn: () => catalogService.getSpecFilterOptions(categoryId),
    enabled: Number.isFinite(categoryId) && categoryId > 0,
    staleTime: 10 * 60 * 1000,
  });
}
