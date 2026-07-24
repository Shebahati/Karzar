"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Controller, useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import { ArrowRight, Bag, InfoCircle, Setting } from "react-iconly";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CategoryLeafCombobox } from "@/features/catalog/components/category-leaf-combobox";
import { ProductSpecificationsForm } from "@/features/catalog/components/product-specifications-form";
import {
  createProductFormSchema,
  productFormDefaults,
  productFormSchema,
  toProductCreatePayload,
  type ProductFormValues,
} from "@/features/catalog/product-schema";
import {
  useBrands,
  useCategorySpecTemplate,
  useCreateProduct,
  useFlatCategories,
} from "@/features/catalog/queries";
import { defaultSpecificationsFromTemplate } from "@/features/catalog/utils/specifications";
import { ApiError } from "@/lib/api-client";
import { STOCK_UNITS, STOCK_UNIT_LABELS } from "@/types/product";

export default function NewProductPage() {
  const router = useRouter();
  const { data: flatCategories = [], isPending: categoriesLoading } = useFlatCategories();
  const { data: brands, isPending: brandsLoading } = useBrands();
  const createProduct = useCreateProduct();

  const form = useForm<ProductFormValues>({
    resolver: zodResolver(productFormSchema),
    defaultValues: productFormDefaults,
    mode: "onBlur",
  });

  const {
    register,
    handleSubmit,
    control,
    setError,
    setValue,
    formState: { errors, isSubmitting },
  } = form;

  const categoryId = useWatch({ control, name: "category_id" });
  const numericCategoryId = categoryId ? Number(categoryId) : 0;

  const { data: specTemplate, isPending: templateLoading } =
    useCategorySpecTemplate(numericCategoryId);

  useEffect(() => {
    if (!specTemplate || !numericCategoryId) return;
    setValue("specifications", defaultSpecificationsFromTemplate(specTemplate), {
      shouldDirty: true,
    });
  }, [specTemplate, numericCategoryId, setValue]);

  async function onSubmit(values: ProductFormValues) {
    const schema = createProductFormSchema(specTemplate ?? null);
    const parsed = schema.safeParse(values);

    if (!parsed.success) {
      for (const issue of parsed.error.issues) {
        const path = issue.path.join(".") as keyof ProductFormValues | string;
        setError(path as Parameters<typeof setError>[0], {
          type: "manual",
          message: issue.message,
        });
      }
      toast.error("لطفاً خطاهای فرم را برطرف کنید.");
      return;
    }

    try {
      const payload = toProductCreatePayload(parsed.data, specTemplate ?? null);
      const created = await createProduct.mutateAsync(payload);
      toast.success("محصول با موفقیت ثبت شد", {
        description: `«${created.name}» به کاتالوگ اضافه شد.`,
      });
      router.push("/catalog/products");
    } catch (err) {
      if (err instanceof ApiError) {
        for (const [field, message] of Object.entries(err.fieldErrors)) {
          if (field in productFormDefaults) {
            setError(field as keyof ProductFormValues, { type: "server", message });
          }
        }
        toast.error("ثبت محصول ناموفق بود", { description: err.message });
      } else {
        toast.error("خطای غیرمنتظره", { description: "لطفاً دوباره تلاش کنید." });
      }
    }
  }

  const pending = isSubmitting || createProduct.isPending;

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="mx-auto flex max-w-6xl flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button asChild variant="ghost" size="icon">
            <Link href="/catalog/products" aria-label="بازگشت">
              <ArrowRight set="light" size={22} primaryColor="currentColor" />
            </Link>
          </Button>
          <div>
            <h2 className="text-2xl font-bold text-[#4F4F4F]">افزودن محصول جدید</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              دسته‌بندی لایه ۳ را انتخاب کنید تا قالب مشخصات فنی بارگذاری شود.
            </p>
          </div>
        </div>
        <div className="hidden gap-3 sm:flex">
          <Button asChild variant="ghost" type="button">
            <Link href="/catalog/products">انصراف</Link>
          </Button>
          <Button type="submit" disabled={pending || !numericCategoryId}>
            {pending ? "در حال ذخیره..." : "ذخیره محصول"}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="flex flex-col gap-6 lg:col-span-2">
          <Card className="border-transparent shadow-card">
            <CardHeader className="flex-row items-center gap-2">
              <Bag set="bulk" size={22} primaryColor="#C22026" />
              <CardTitle className="text-[#4F4F4F]">اطلاعات پایه</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-1 gap-5 sm:grid-cols-2">
              <Field
                label="نام محصول"
                htmlFor="name"
                required
                error={errors.name?.message}
                className="sm:col-span-2"
              >
                <Input
                  id="name"
                  placeholder="مثال: کولیس دیجیتال ۰-۱۵۰mm"
                  aria-invalid={Boolean(errors.name)}
                  {...register("name")}
                />
              </Field>

              <Field
                label="توضیحات"
                htmlFor="description"
                error={errors.description?.message}
                className="sm:col-span-2"
              >
                <textarea
                  id="description"
                  rows={4}
                  className="w-full rounded-xl border border-input bg-white px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-ring/40"
                  placeholder="توضیحات تکمیلی محصول برای نمایش در فروشگاه"
                  aria-invalid={Boolean(errors.description)}
                  {...register("description")}
                />
              </Field>

              <Field label="کد محصول (SKU)" htmlFor="sku" required error={errors.sku?.message}>
                <Input
                  id="sku"
                  dir="ltr"
                  placeholder="1108-150"
                  className="text-start"
                  aria-invalid={Boolean(errors.sku)}
                  {...register("sku")}
                />
              </Field>

              <Field
                label="دسته‌بندی (لایه ۳)"
                required
                error={errors.category_id?.message}
                className="sm:col-span-2"
              >
                <Controller
                  control={control}
                  name="category_id"
                  render={({ field }) => (
                    <CategoryLeafCombobox
                      categories={flatCategories}
                      value={field.value}
                      onChange={field.onChange}
                      loading={categoriesLoading}
                      error={Boolean(errors.category_id)}
                    />
                  )}
                />
              </Field>

              <Field
                label="برند"
                error={errors.brand_id?.message}
                hint={brandsLoading ? "در حال بارگذاری برندها..." : "اختیاری"}
              >
                <Controller
                  control={control}
                  name="brand_id"
                  render={({ field }) => (
                    <Select value={field.value || ""} onValueChange={field.onChange}>
                      <SelectTrigger>
                        <SelectValue placeholder="انتخاب برند" />
                      </SelectTrigger>
                      <SelectContent>
                        {(brands ?? []).map((brand) => (
                          <SelectItem key={brand.id} value={String(brand.id)}>
                            {brand.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
              </Field>

              <Field
                label="متن گارانتی"
                htmlFor="warranty_text"
                error={errors.warranty_text?.message}
                className="sm:col-span-2"
              >
                <Input
                  id="warranty_text"
                  placeholder="مثال: ۱۸ ماه گارانتی شرکتی"
                  aria-invalid={Boolean(errors.warranty_text)}
                  {...register("warranty_text")}
                />
              </Field>
            </CardContent>
          </Card>

          <ProductSpecificationsForm
            control={control}
            register={register}
            setValue={setValue}
            errors={errors}
            template={specTemplate ?? null}
            templateLoading={templateLoading}
            categorySelected={numericCategoryId > 0}
          />
        </div>

        <div className="flex flex-col gap-6">
          <Card className="border-transparent shadow-card">
            <CardHeader className="flex-row items-center gap-2">
              <InfoCircle set="bulk" size={22} primaryColor="#C22026" />
              <CardTitle className="text-[#4F4F4F]">قیمت و موجودی</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-5">
              <Field
                label="قیمت پایه (تومان)"
                htmlFor="base_price"
                error={errors.base_price?.message}
                hint="در صورت استعلامی بودن خالی بگذارید"
              >
                <Input
                  id="base_price"
                  dir="ltr"
                  inputMode="numeric"
                  placeholder="1850000"
                  className="text-start tnum"
                  aria-invalid={Boolean(errors.base_price)}
                  {...register("base_price")}
                />
              </Field>

              <Field
                label="قیمت قبل از تخفیف (تومان)"
                htmlFor="original_price"
                error={errors.original_price?.message}
                hint="در صورت تخفیف، قیمت خط‌خورده نمایش داده می‌شود"
              >
                <Input
                  id="original_price"
                  dir="ltr"
                  inputMode="numeric"
                  placeholder="2100000"
                  className="text-start tnum line-through decoration-muted-foreground/60"
                  aria-invalid={Boolean(errors.original_price)}
                  {...register("original_price")}
                />
              </Field>

              <div className="grid grid-cols-2 gap-4">
                <Field
                  label="موجودی"
                  htmlFor="stock_quantity"
                  required
                  error={errors.stock_quantity?.message}
                >
                  <Input
                    id="stock_quantity"
                    dir="ltr"
                    inputMode="decimal"
                    className="text-start tnum"
                    aria-invalid={Boolean(errors.stock_quantity)}
                    {...register("stock_quantity")}
                  />
                </Field>

                <Field label="واحد" error={errors.stock_unit?.message}>
                  <Controller
                    control={control}
                    name="stock_unit"
                    render={({ field }) => (
                      <Select value={field.value} onValueChange={field.onChange}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {STOCK_UNITS.map((unit) => (
                            <SelectItem key={unit} value={unit}>
                              {STOCK_UNIT_LABELS[unit]}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  />
                </Field>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <Field
                  label="مالیات (٪)"
                  htmlFor="tax_percent"
                  required
                  error={errors.tax_percent?.message}
                >
                  <Input
                    id="tax_percent"
                    dir="ltr"
                    inputMode="decimal"
                    className="text-start tnum"
                    aria-invalid={Boolean(errors.tax_percent)}
                    {...register("tax_percent")}
                  />
                </Field>

                <Field label="وزن (گرم)" htmlFor="weight_grams" error={errors.weight_grams?.message}>
                  <Input
                    id="weight_grams"
                    dir="ltr"
                    inputMode="decimal"
                    className="text-start tnum"
                    aria-invalid={Boolean(errors.weight_grams)}
                    {...register("weight_grams")}
                  />
                </Field>
              </div>
            </CardContent>
          </Card>

          <Card className="border-transparent shadow-card">
            <CardHeader className="flex-row items-center gap-2">
              <Setting set="bulk" size={22} primaryColor="#C22026" />
              <CardTitle className="text-[#4F4F4F]">تنظیمات انتشار</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-5">
              <Controller
                control={control}
                name="is_active"
                render={({ field }) => (
                  <label className="flex cursor-pointer items-center justify-between gap-3 rounded-xl bg-[#F7F7F7] px-4 py-3 shadow-soft">
                    <span className="flex flex-col">
                      <span className="text-sm font-bold text-[#4F4F4F]">محصول فعال</span>
                      <span className="text-xs text-muted-foreground">نمایش در فروشگاه</span>
                    </span>
                    <Switch checked={field.value} onCheckedChange={field.onChange} />
                  </label>
                )}
              />

              <Controller
                control={control}
                name="is_original"
                render={({ field }) => (
                  <label className="flex cursor-pointer items-center justify-between gap-3 rounded-xl bg-[#F7F7F7] px-4 py-3 shadow-soft">
                    <span className="flex flex-col">
                      <span className="text-sm font-bold text-[#4F4F4F]">کالای اورجینال</span>
                      <span className="text-xs text-muted-foreground">دارای اصالت برند</span>
                    </span>
                    <Switch checked={field.value} onCheckedChange={field.onChange} />
                  </label>
                )}
              />

              <Field
                label="لینک کاتالوگ PDF"
                htmlFor="pdf_catalog_url"
                error={errors.pdf_catalog_url?.message}
              >
                <Input
                  id="pdf_catalog_url"
                  dir="ltr"
                  placeholder="https://..."
                  className="text-start"
                  aria-invalid={Boolean(errors.pdf_catalog_url)}
                  {...register("pdf_catalog_url")}
                />
              </Field>
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="flex gap-3 sm:hidden">
        <Button type="submit" className="flex-1" disabled={pending || !numericCategoryId}>
          {pending ? "در حال ذخیره..." : "ذخیره محصول"}
        </Button>
        <Button asChild variant="ghost" type="button">
          <Link href="/catalog/products">انصراف</Link>
        </Button>
      </div>
    </form>
  );
}
