"use client";



import {

  useMutation,

  useQuery,

  useQueryClient,

  keepPreviousData,

} from "@tanstack/react-query";



import { catalogService } from "@/services/catalog";

import type { ApiError } from "@/lib/api-client";

import type {

  BrandCreatePayload,

  BrandDeleteResult,

  BrandUpdatePayload,

  CategoryCreatePayload,

  CategoryDeleteResult,

  CategoryFlat,

  CategoryUpdatePayload,

} from "@/types/category";

import type {

  ProductCreatePayload,

  ProductDetail,

  ProductListParams,

  ProductUpdatePayload,

} from "@/types/product";



/** Centralized, hierarchical query keys for safe cache invalidation. */

export const catalogKeys = {

  all: ["catalog"] as const,

  products: () => [...catalogKeys.all, "products"] as const,

  productList: (params: ProductListParams) =>

    [...catalogKeys.products(), "list", params] as const,

  product: (id: number) => [...catalogKeys.products(), "detail", id] as const,
  productsByIds: (ids: number[]) => [...catalogKeys.products(), "by-ids", ids] as const,

  categories: () => [...catalogKeys.all, "categories"] as const,

  categoriesFlat: () => [...catalogKeys.all, "categories", "flat"] as const,

  categorySpecTemplate: (id: number) =>

    [...catalogKeys.categories(), "spec-template", id] as const,

  brands: () => [...catalogKeys.all, "brands"] as const,

};



export function useProducts(params: ProductListParams = {}) {

  return useQuery({

    queryKey: catalogKeys.productList(params),

    queryFn: () => catalogService.listProducts(params),

    placeholderData: keepPreviousData,

  });

}



export function useProduct(id: number, enabled = true) {

  return useQuery({

    queryKey: catalogKeys.product(id),

    queryFn: () => catalogService.getProduct(id),

    enabled: enabled && Number.isFinite(id),

  });

}



export function useProductsByIds(ids: number[]) {
  return useQuery({
    queryKey: catalogKeys.productsByIds(ids),
    queryFn: () => catalogService.getProductsByIds(ids),
    enabled: ids.length > 0,
    staleTime: 5 * 60 * 1000,
  });
}



export function useFlatCategories() {

  return useQuery({

    queryKey: catalogKeys.categoriesFlat(),

    queryFn: () => catalogService.listFlatCategories(),

    staleTime: 10 * 60 * 1000,

  });

}



export function useCategorySpecTemplate(categoryId: number) {

  return useQuery({

    queryKey: catalogKeys.categorySpecTemplate(categoryId),

    queryFn: () => catalogService.getCategorySpecTemplate(categoryId),

    enabled: Number.isFinite(categoryId) && categoryId > 0,

    staleTime: 5 * 60 * 1000,

  });

}



export function useCategories() {

  return useQuery({

    queryKey: catalogKeys.categories(),

    queryFn: () => catalogService.listCategories(),

    staleTime: 10 * 60 * 1000,

  });

}



export function useBrands() {

  return useQuery({

    queryKey: catalogKeys.brands(),

    queryFn: () => catalogService.listBrands(),

    staleTime: 10 * 60 * 1000,

  });

}



export function useCreateProduct() {

  const queryClient = useQueryClient();

  return useMutation<ProductDetail, ApiError, ProductCreatePayload>({

    mutationFn: (payload) => catalogService.createProduct(payload),

    onSuccess: () => {

      void queryClient.invalidateQueries({ queryKey: catalogKeys.products() });

    },

  });

}



export function useUpdateProduct() {

  const queryClient = useQueryClient();

  return useMutation<ProductDetail, ApiError, { id: number; payload: ProductUpdatePayload }>({

    mutationFn: ({ id, payload }) => catalogService.updateProduct(id, payload),

    onSuccess: (data) => {

      void queryClient.invalidateQueries({ queryKey: catalogKeys.products() });

      void queryClient.setQueryData(catalogKeys.product(data.id), data);

    },

  });

}



export function useDeleteProduct() {

  const queryClient = useQueryClient();

  return useMutation<void, ApiError, { id: number; stepUpToken: string }>({

    mutationFn: ({ id, stepUpToken }) => catalogService.deleteProduct(id, stepUpToken),

    onSuccess: () => {

      void queryClient.invalidateQueries({ queryKey: catalogKeys.products() });

    },

  });

}



export function useCreateCategory() {

  const queryClient = useQueryClient();

  return useMutation<CategoryFlat, ApiError, CategoryCreatePayload>({

    mutationFn: (payload) => catalogService.createCategory(payload),

    onSuccess: () => {

      void queryClient.invalidateQueries({ queryKey: catalogKeys.categories() });

      void queryClient.invalidateQueries({ queryKey: catalogKeys.categoriesFlat() });

    },

  });

}



export function useUpdateCategory() {

  const queryClient = useQueryClient();

  return useMutation<CategoryFlat, ApiError, { id: number; payload: CategoryUpdatePayload }>({

    mutationFn: ({ id, payload }) => catalogService.updateCategory(id, payload),

    onSuccess: () => {

      void queryClient.invalidateQueries({ queryKey: catalogKeys.categories() });

      void queryClient.invalidateQueries({ queryKey: catalogKeys.categoriesFlat() });

    },

  });

}



export function useDeleteCategory() {

  const queryClient = useQueryClient();

  return useMutation<
    CategoryDeleteResult,
    ApiError,
    { id: number; stepUpToken: string; targetCategoryId?: number }
  >({

    mutationFn: ({ id, stepUpToken, targetCategoryId }) =>
      catalogService.deleteCategory(id, stepUpToken, targetCategoryId),

    onSuccess: () => {

      void queryClient.invalidateQueries({ queryKey: catalogKeys.categories() });

      void queryClient.invalidateQueries({ queryKey: catalogKeys.categoriesFlat() });

      void queryClient.invalidateQueries({ queryKey: catalogKeys.products() });

    },

  });

}



export function useCreateBrand() {

  const queryClient = useQueryClient();

  return useMutation({

    mutationFn: (payload: BrandCreatePayload) => catalogService.createBrand(payload),

    onSuccess: () => {

      void queryClient.invalidateQueries({ queryKey: catalogKeys.brands() });

    },

  });

}



export function useUpdateBrand() {

  const queryClient = useQueryClient();

  return useMutation({

    mutationFn: ({ id, payload }: { id: number; payload: BrandUpdatePayload }) =>

      catalogService.updateBrand(id, payload),

    onSuccess: () => {

      void queryClient.invalidateQueries({ queryKey: catalogKeys.brands() });

    },

  });

}



export function useDeleteBrand() {

  const queryClient = useQueryClient();

  return useMutation<BrandDeleteResult, ApiError, { id: number; stepUpToken: string }>({

    mutationFn: ({ id, stepUpToken }) => catalogService.deleteBrand(id, stepUpToken),

    onSuccess: () => {

      void queryClient.invalidateQueries({ queryKey: catalogKeys.brands() });

      void queryClient.invalidateQueries({ queryKey: catalogKeys.products() });

    },

  });

}



export function useRestoreProduct() {

  const queryClient = useQueryClient();

  return useMutation({

    mutationFn: ({ id, stepUpToken }: { id: number; stepUpToken?: string }) =>
      catalogService.restoreProduct(id, stepUpToken),

    onSuccess: () => {

      void queryClient.invalidateQueries({ queryKey: catalogKeys.products() });

    },

  });

}



export function useProductStock(id: number, enabled = true) {

  return useQuery({

    queryKey: [...catalogKeys.product(id), "stock"] as const,

    queryFn: () => catalogService.getProductStock(id),

    enabled: enabled && Number.isFinite(id),

  });

}



export function useAdjustProductStock(id: number) {

  const queryClient = useQueryClient();

  return useMutation({

    mutationFn: (payload: import("@/types/product").ProductStockAdjustPayload) =>

      catalogService.adjustProductStock(id, payload),

    onSuccess: () => {

      void queryClient.invalidateQueries({ queryKey: catalogKeys.product(id) });

      void queryClient.invalidateQueries({ queryKey: catalogKeys.products() });

    },

  });

}



export function useUploadProductImage(id: number) {

  const queryClient = useQueryClient();

  return useMutation({

    mutationFn: (file: File) => catalogService.uploadProductImage(id, file),

    onSuccess: () => {

      void queryClient.invalidateQueries({ queryKey: catalogKeys.product(id) });

    },

  });

}



export function useAddProductImageByUrl(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (imageUrl: string) => catalogService.addProductImageByUrl(id, imageUrl),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: catalogKeys.product(id) });
    },
  });
}



export function useSetPrimaryProductImage(productId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (imageId: number) => catalogService.setPrimaryProductImage(productId, imageId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: catalogKeys.product(productId) });
    },
  });
}



export function useReorderProductImages(productId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (imageIds: number[]) => catalogService.reorderProductImages(productId, imageIds),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: catalogKeys.product(productId) });
    },
  });
}



export function useDeleteProductImage(productId: number) {

  const queryClient = useQueryClient();

  return useMutation({

    mutationFn: (imageId: number) => catalogService.deleteProductImage(productId, imageId),

    onSuccess: () => {

      void queryClient.invalidateQueries({ queryKey: catalogKeys.product(productId) });

    },

  });

}



export function useVerifyPin() {

  return useMutation<{ secure_token: string }, ApiError, string>({

    mutationFn: (pin) => catalogService.verifyPin(pin),

  });

}



export function useProductStatistics() {

  return useQuery({

    queryKey: [...catalogKeys.all, "statistics"] as const,

    queryFn: () => catalogService.getStatistics(),

    staleTime: 60 * 1000,

  });

}



export function useProductChangeLog(productId: number, enabled = true) {

  return useQuery({

    queryKey: [...catalogKeys.product(productId), "change-log"] as const,

    queryFn: () => catalogService.getChangeLog(productId),

    enabled: enabled && Number.isFinite(productId) && productId > 0,

  });

}



export function useBulkStockAdjust() {
  const queryClient = useQueryClient();

  return useMutation<
    import("@/types/product").BulkStockAdjustResponse,
    ApiError,
    {
      items: import("@/types/product").BulkStockAdjustItem[];
      stepUpToken: string;
    }
  >({
    mutationFn: ({ items, stepUpToken }) =>
      catalogService.bulkStockAdjust(items, stepUpToken),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: catalogKeys.products() });
    },
  });
}


