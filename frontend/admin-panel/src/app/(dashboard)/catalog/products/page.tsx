"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ArrowRight, Bag2, Delete, Edit, Filter, Plus, Swap, Search } from "react-iconly";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { StepUpDialog } from "@/components/step-up-dialog";
import { CategoryLeafCombobox } from "@/features/catalog/components/category-leaf-combobox";
import {
  useBrands,
  useBulkStockAdjust,
  useDeleteProduct,
  useFlatCategories,
  useProducts,
} from "@/features/catalog/queries";
import { enrichFlatCategories } from "@/features/catalog/utils/category-tree";
import { ApiError } from "@/lib/api-client";
import { formatNumber, formatToman } from "@/lib/utils";
import type { ProductSummary } from "@/types/product";

const PAGE_SIZE = 50;

function StockBadge({ status }: { status: string }) {
  if (status === "out_of_stock") return <Badge variant="danger">ناموجود</Badge>;
  if (status === "low_stock") return <Badge variant="warning">موجودی کم</Badge>;
  return <Badge variant="success">موجود</Badge>;
}

function categoryHierarchy(product: ProductSummary): string {
  if (product.category?.hierarchy_label) return product.category.hierarchy_label;
  if (product.category?.breadcrumb?.length) return product.category.breadcrumb.join(" > ");
  return product.category?.name ?? "—";
}

export default function ProductsListPage() {
  const [search, setSearch] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [brandId, setBrandId] = useState("");
  const [skip, setSkip] = useState(0);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [bulkOpen, setBulkOpen] = useState(false);
  const [bulkDeltas, setBulkDeltas] = useState<Record<number, string>>({});
  const [bulkReason, setBulkReason] = useState("");

  // Reset pagination whenever a filter changes (adjust-state-on-render pattern
  // — avoids a cascading-render effect just to zero out `skip`).
  const [prevFilters, setPrevFilters] = useState({ search, categoryId, brandId });
  if (
    prevFilters.search !== search ||
    prevFilters.categoryId !== categoryId ||
    prevFilters.brandId !== brandId
  ) {
    setPrevFilters({ search, categoryId, brandId });
    setSkip(0);
  }

  const listParams = useMemo(
    () => ({
      skip,
      limit: PAGE_SIZE,
      search: search.trim() || undefined,
      category_id: categoryId ? Number(categoryId) : undefined,
      brand_id: brandId ? Number(brandId) : undefined,
    }),
    [skip, search, categoryId, brandId],
  );

  const { data, isPending, isError, error, refetch, isFetching } = useProducts(listParams);
  const { data: flatCategories = [] } = useFlatCategories();
  const categories = useMemo(() => enrichFlatCategories(flatCategories), [flatCategories]);
  const { data: brands = [] } = useBrands();

  const deleteProduct = useDeleteProduct();
  const bulkStockAdjust = useBulkStockAdjust();
  const [target, setTarget] = useState<ProductSummary | null>(null);
  const [bulkStepUpOpen, setBulkStepUpOpen] = useState(false);
  const [pendingBulkItems, setPendingBulkItems] = useState<
    Array<{ product_id: number; quantity_delta: number; reason?: string }>
  >([]);

  const products = useMemo(() => data?.data ?? [], [data]);
  const meta = data?.meta;
  const rangeStart = meta ? Math.min(meta.skip + 1, meta.total_count) : 0;
  const rangeEnd = meta ? Math.min(meta.skip + meta.limit, meta.total_count) : 0;

  function handleVerified(stepUpToken: string) {
    if (!target) return;
    const productName = target.name;
    deleteProduct.mutate(
      { id: target.id, stepUpToken },
      {
        onSuccess: () => {
          toast.success("محصول حذف شد", { description: `«${productName}» حذف گردید.` });
          setTarget(null);
        },
        onError: (err) => {
          const message = err instanceof ApiError ? err.message : "حذف ناموفق بود.";
          toast.error("حذف ناموفق بود", { description: message });
          setTarget(null);
        },
      },
    );
  }

  function handleBulkVerified(stepUpToken: string) {
    bulkStockAdjust.mutate(
      { items: pendingBulkItems, stepUpToken },
      {
        onSuccess: (result) => {
          toast.success("موجودی به‌صورت انبوه به‌روزرسانی شد", {
            description: `${formatNumber(result.updated_product_ids.length)} محصول به‌روزرسانی شد.`,
          });
          setBulkStepUpOpen(false);
          setPendingBulkItems([]);
          setBulkOpen(false);
          setSelectedIds(new Set());
        },
        onError: (err) => {
          toast.error(err instanceof ApiError ? err.message : "به‌روزرسانی انبوه ناموفق بود.");
          setBulkStepUpOpen(false);
        },
      },
    );
  }

  function toggleSelected(id: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectAllOnPage() {
    setSelectedIds((prev) => {
      const allSelected = products.every((p) => prev.has(p.id));
      if (allSelected) {
        const next = new Set(prev);
        products.forEach((p) => next.delete(p.id));
        return next;
      }
      const next = new Set(prev);
      products.forEach((p) => next.add(p.id));
      return next;
    });
  }

  function openBulkDialog() {
    const initial: Record<number, string> = {};
    selectedIds.forEach((id) => {
      initial[id] = "0";
    });
    setBulkDeltas(initial);
    setBulkReason("");
    setBulkOpen(true);
  }

  function submitBulkAdjust() {
    const items = Object.entries(bulkDeltas)
      .map(([id, delta]) => ({ product_id: Number(id), quantity_delta: Number(delta) }))
      .filter((item) => Number.isFinite(item.quantity_delta) && item.quantity_delta !== 0);

    if (items.length === 0) {
      toast.error("حداقل یک تغییر موجودی غیر صفر وارد کنید.");
      return;
    }

    setPendingBulkItems(
      items.map((item) => ({ ...item, reason: bulkReason.trim() || undefined })),
    );
    setBulkStepUpOpen(true);
  }

  const hasFilters = Boolean(search.trim() || categoryId || brandId);
  const selectedProducts = products.filter((p) => selectedIds.has(p.id));

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-ink">مدیریت محصولات</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {data ? `${formatNumber(data.meta.total_count)} محصول` : "کاتالوگ فروشگاه"}
          </p>
        </div>
        <Button asChild variant="outline">
          <Link href="/catalog/products/deleted">محصولات حذف‌شده</Link>
        </Button>
        <Button asChild>
          <Link href="/catalog/products/new">
            <Plus set="bold" size={20} primaryColor="#FFFFFF" />
            افزودن محصول
          </Link>
        </Button>
      </div>

      <div className="rounded-xl bg-white p-4 shadow-sm">
        <div className="mb-3 flex items-center gap-2 text-sm font-bold text-[#4F4F4F]">
          <Filter set="light" size={18} primaryColor="#C22026" />
          فیلتر پیشرفته
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <div className="relative">
            <span className="pointer-events-none absolute inset-y-0 start-3 flex items-center text-muted-foreground">
              <Search set="light" size={18} />
            </span>
            <Input
              placeholder="جستجو نام، SKU یا برند..."
              className="ps-10"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <CategoryLeafCombobox
            categories={categories}
            value={categoryId}
            onChange={setCategoryId}
            loading={false}
          />
          <Select value={brandId || "all"} onValueChange={(v) => setBrandId(v === "all" ? "" : v)}>
            <SelectTrigger>
              <SelectValue placeholder="همه برندها" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">همه برندها</SelectItem>
              {brands.map((brand) => (
                <SelectItem key={brand.id} value={String(brand.id)}>
                  {brand.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        {hasFilters && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="mt-3"
            onClick={() => {
              setSearch("");
              setCategoryId("");
              setBrandId("");
            }}
          >
            پاک کردن فیلترها
          </Button>
        )}
      </div>

      {selectedIds.size > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-accent px-4 py-3">
          <span className="text-sm font-bold text-accent-foreground">
            {formatNumber(selectedIds.size)} محصول انتخاب شده
          </span>
          <div className="flex items-center gap-2">
            <Button type="button" variant="outline" size="sm" onClick={() => setSelectedIds(new Set())}>
              لغو انتخاب
            </Button>
            <Button type="button" size="sm" onClick={openBulkDialog}>
              بروزرسانی انبوه موجودی
            </Button>
          </div>
        </div>
      )}

      <Card className="border-transparent shadow-sm">
        <CardContent className="p-0">
          {isPending ? (
            <div className="flex flex-col gap-3 p-6">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : isError ? (
            <div className="flex flex-col items-center gap-3 py-16 text-center">
              <Delete set="bulk" size={44} primaryColor="#C22026" />
              <p className="text-sm font-bold text-foreground">
                {error instanceof ApiError ? error.message : "خطا در دریافت محصولات"}
              </p>
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                تلاش مجدد
              </Button>
            </div>
          ) : products.length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-16 text-center">
              <Bag2 set="bulk" size={48} primaryColor="#BDBDBD" />
              <p className="text-sm font-bold text-foreground">محصولی یافت نشد</p>
              <p className="max-w-xs text-xs text-muted-foreground">
                {hasFilters
                  ? "نتیجه‌ای برای فیلترهای شما وجود ندارد."
                  : "هنوز محصولی ثبت نشده است."}
              </p>
            </div>
          ) : (
            <div className="flex flex-col p-3">
              <div className="hidden px-4 py-2 text-xs font-bold text-muted-foreground md:grid md:grid-cols-[28px_1fr_1.2fr_120px_100px_88px] md:items-center md:gap-4">
                <input
                  type="checkbox"
                  className="h-4 w-4 cursor-pointer accent-primary"
                  checked={products.length > 0 && products.every((p) => selectedIds.has(p.id))}
                  onChange={toggleSelectAllOnPage}
                  aria-label="انتخاب همه"
                />
                <span>محصول</span>
                <span>دسته‌بندی</span>
                <span>قیمت پایه</span>
                <span>وضعیت</span>
                <span />
              </div>
              <ul className={`flex flex-col gap-1 ${isFetching ? "opacity-60" : ""}`}>
                {products.map((product) => (
                  <li
                    key={product.id}
                    className="grid grid-cols-1 items-center gap-2 rounded-lg px-4 py-3 transition-colors hover:bg-[#F7F7F7] md:grid-cols-[28px_1fr_1.2fr_120px_100px_88px] md:gap-4"
                  >
                    <input
                      type="checkbox"
                      className="h-4 w-4 cursor-pointer accent-primary"
                      checked={selectedIds.has(product.id)}
                      onChange={() => toggleSelected(product.id)}
                      aria-label={`انتخاب ${product.name}`}
                    />
                    <div className="flex items-center gap-3">
                      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-accent text-primary">
                        <Bag2 set="bulk" size={22} primaryColor="#C22026" />
                      </div>
                      <div className="flex min-w-0 flex-col">
                        <span className="truncate text-sm font-bold text-[#4F4F4F]">
                          {product.name}
                        </span>
                        <span dir="ltr" className="text-start text-xs text-muted-foreground">
                          {product.sku}
                        </span>
                      </div>
                    </div>
                    <span className="truncate text-sm text-muted-foreground" title={categoryHierarchy(product)}>
                      {categoryHierarchy(product)}
                    </span>
                    <span className="text-sm font-bold text-foreground tnum">
                      {formatToman(product.base_price)}
                    </span>
                    <span>
                      <StockBadge status={product.stock_status} />
                    </span>
                    <div className="flex justify-end gap-1">
                      <Button
                        asChild
                        variant="ghost"
                        size="icon"
                        aria-label="ویرایش محصول"
                      >
                        <Link href={`/catalog/products/${product.id}/edit`}>
                          <Edit set="light" size={20} primaryColor="currentColor" />
                        </Link>
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label="حذف محصول"
                        className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                        onClick={() => setTarget(product)}
                      >
                        <Delete set="light" size={20} primaryColor="currentColor" />
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>

              {meta && meta.total_count > meta.limit && (
                <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-border px-4 pt-4">
                  <span className="text-xs text-muted-foreground tnum">
                    نمایش {formatNumber(rangeStart)} تا {formatNumber(rangeEnd)} از{" "}
                    {formatNumber(meta.total_count)} محصول
                  </span>
                  <div className="flex items-center gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={!meta.has_prev || isFetching}
                      onClick={() => setSkip((prev) => Math.max(0, prev - PAGE_SIZE))}
                    >
                      <ArrowRight set="light" size={16} />
                      قبلی
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={!meta.has_next || isFetching}
                      onClick={() => setSkip((prev) => prev + PAGE_SIZE)}
                    >
                      بعدی
                      <ArrowLeft set="light" size={16} />
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <StepUpDialog
        open={target !== null}
        onOpenChange={(open) => (!open ? setTarget(null) : undefined)}
        onVerified={handleVerified}
        actionPending={deleteProduct.isPending}
        title="حذف محصول"
        description={
          target
            ? `برای حذف «${target.name}» کد امنیتی مدیر را وارد کنید.`
            : undefined
        }
      />

      <StepUpDialog
        open={bulkStepUpOpen}
        onOpenChange={(open) => {
          if (!open) {
            setBulkStepUpOpen(false);
            setPendingBulkItems([]);
          }
        }}
        onVerified={handleBulkVerified}
        actionPending={bulkStockAdjust.isPending}
        title="تأیید بروزرسانی انبوه موجودی"
        description={`برای اعمال تغییر موجودی روی ${formatNumber(pendingBulkItems.length)} محصول، کد امنیتی مدیر را وارد کنید.`}
      />

      <Dialog open={bulkOpen} onOpenChange={setBulkOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>بروزرسانی انبوه موجودی</DialogTitle>
            <DialogDescription>
              برای هر محصول مقدار تغییر موجودی را وارد کنید (مثبت برای افزایش، منفی برای کاهش).
            </DialogDescription>
          </DialogHeader>

          <div className="flex max-h-64 flex-col gap-3 overflow-y-auto">
            {selectedProducts.map((product) => (
              <div key={product.id} className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-bold text-foreground">{product.name}</p>
                  <p dir="ltr" className="text-start text-xs text-muted-foreground">
                    {product.sku}
                  </p>
                </div>
                <Input
                  type="number"
                  dir="ltr"
                  className="w-28 text-start tnum"
                  value={bulkDeltas[product.id] ?? "0"}
                  onChange={(e) =>
                    setBulkDeltas((prev) => ({ ...prev, [product.id]: e.target.value }))
                  }
                />
              </div>
            ))}
          </div>

          <Textarea
            placeholder="دلیل تغییر موجودی (اختیاری)"
            value={bulkReason}
            onChange={(e) => setBulkReason(e.target.value)}
            rows={2}
          />

          <DialogFooter>
            <Button
              type="button"
              onClick={submitBulkAdjust}
              disabled={bulkStockAdjust.isPending}
              className="flex-1"
            >
              {bulkStockAdjust.isPending ? (
                "در حال ذخیره..."
              ) : (
                <>
                  <Swap set="bold" size={18} primaryColor="#FFFFFF" />
                  اعمال تغییرات
                </>
              )}
            </Button>
            <Button type="button" variant="ghost" onClick={() => setBulkOpen(false)}>
              انصراف
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
