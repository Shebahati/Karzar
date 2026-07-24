"use client";

import {
  useFieldArray,
  useWatch,
  type Control,
  type FieldErrors,
  type UseFormRegister,
  type UseFormSetValue,
} from "react-hook-form";
import { Delete, Document, Plus, Setting, Work } from "react-iconly";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CreatableCombobox } from "@/components/ui/creatable-combobox";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { TagInput } from "@/components/ui/tag-input";
import { Skeleton } from "@/components/ui/skeleton";
import type { ProductFormValues } from "@/features/catalog/product-schema";
import type { CategorySpecTemplate } from "@/types/spec-template";

interface ProductSpecificationsFormProps {
  control: Control<ProductFormValues>;
  register: UseFormRegister<ProductFormValues>;
  setValue: UseFormSetValue<ProductFormValues>;
  errors: FieldErrors<ProductFormValues>;
  template: CategorySpecTemplate | null;
  templateLoading?: boolean;
  categorySelected: boolean;
}

function TechnicalSpecRow({
  control,
  setValue,
  index,
  template,
  onRemove,
  keyError,
  valueError,
}: {
  control: Control<ProductFormValues>;
  setValue: UseFormSetValue<ProductFormValues>;
  index: number;
  template: CategorySpecTemplate;
  onRemove: () => void;
  keyError?: string;
  valueError?: string;
}) {
  const watchedKey = useWatch({
    control,
    name: `specifications.technical_specs.${index}.key`,
  });
  const watchedValue = useWatch({
    control,
    name: `specifications.technical_specs.${index}.value`,
  });
  const valueOptions =
    template.technical_specs.value_options[watchedKey ?? ""] ??
    template.technical_specs.suggested_keys;

  return (
    <div className="flex flex-col gap-2">
      <div className="grid grid-cols-1 gap-2 md:grid-cols-[1fr_1fr_auto]">
        <CreatableCombobox
          value={watchedKey ?? ""}
          onChange={(next) =>
            setValue(`specifications.technical_specs.${index}.key`, next, { shouldDirty: true })
          }
          options={template.technical_specs.suggested_keys}
          placeholder="کلید (مثال: accuracy)"
          aria-invalid={Boolean(keyError)}
        />
        <CreatableCombobox
          value={watchedValue ?? ""}
          onChange={(next) =>
            setValue(`specifications.technical_specs.${index}.value`, next, { shouldDirty: true })
          }
          options={valueOptions}
          placeholder="مقدار (مثال: ±0.02mm)"
          aria-invalid={Boolean(valueError)}
        />
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
          onClick={onRemove}
          aria-label="حذف ردیف"
        >
          <Delete set="light" size={20} primaryColor="currentColor" />
        </Button>
      </div>
      {(keyError || valueError) && (
        <p className="text-xs text-destructive">{keyError ?? valueError}</p>
      )}
    </div>
  );
}

function DimensionRow({
  control,
  register,
  setValue,
  index,
  template,
  onRemove,
  keyError,
  valueError,
}: {
  control: Control<ProductFormValues>;
  register: UseFormRegister<ProductFormValues>;
  setValue: UseFormSetValue<ProductFormValues>;
  index: number;
  template: CategorySpecTemplate;
  onRemove: () => void;
  keyError?: string;
  valueError?: string;
}) {
  const watchedKey = useWatch({ control, name: `specifications.dimensions.${index}.key` });

  return (
    <div className="flex flex-col gap-2">
      <div className="grid grid-cols-1 gap-2 md:grid-cols-[1fr_1fr_auto]">
        <CreatableCombobox
          value={watchedKey ?? ""}
          onChange={(next) =>
            setValue(`specifications.dimensions.${index}.key`, next, { shouldDirty: true })
          }
          options={template.dimensions.suggested_keys}
          placeholder="کلید (مثال: L)"
          aria-invalid={Boolean(keyError)}
        />
        <div className="relative">
          <Input
            type="number"
            step="any"
            min={0}
            dir="ltr"
            className="pe-14 text-start tnum"
            placeholder="0"
            aria-invalid={Boolean(valueError)}
            {...register(`specifications.dimensions.${index}.value` as const)}
          />
          <span className="pointer-events-none absolute inset-y-0 end-3 flex items-center text-xs font-bold text-muted-foreground">
            mm
          </span>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
          onClick={onRemove}
          aria-label="حذف بعد"
        >
          <Delete set="light" size={20} primaryColor="currentColor" />
        </Button>
      </div>
      {(keyError || valueError) && (
        <p className="text-xs text-destructive">{keyError ?? valueError}</p>
      )}
    </div>
  );
}

export function ProductSpecificationsForm({
  control,
  register,
  setValue,
  errors,
  template,
  templateLoading,
  categorySelected,
}: ProductSpecificationsFormProps) {
  const techArray = useFieldArray({ control, name: "specifications.technical_specs" });
  const dimArray = useFieldArray({ control, name: "specifications.dimensions" });

  const featureToggles = useWatch({ control, name: "specifications.featureToggles" }) ?? {};
  const featureDetails = useWatch({ control, name: "specifications.featureDetails" }) ?? {};

  const specErrors = errors.specifications;

  if (!categorySelected) {
    return (
      <Card className="border-transparent shadow-card">
        <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
          <Document set="bulk" size={40} primaryColor="#BDBDBD" />
          <p className="text-sm text-muted-foreground">
            ابتدا یک دسته‌بندی لایه ۳ انتخاب کنید تا بخش اطلاعات محصول بارگذاری شود.
          </p>
        </CardContent>
      </Card>
    );
  }

  if (templateLoading || !template) {
    return (
      <Card className="border-transparent shadow-card">
        <CardContent className="flex flex-col gap-3 p-6">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-2">
        <Work set="bulk" size={22} primaryColor="#C22026" />
        <div>
          <h3 className="text-lg font-bold text-[#4F4F4F]">اطلاعات محصول</h3>
          <p className="text-xs text-muted-foreground">{template.breadcrumb.join(" / ")}</p>
        </div>
      </div>

      <Card className="border-transparent shadow-card">
        <CardHeader className="flex-row items-center gap-2 pb-3">
          <Setting set="bulk" size={20} primaryColor="#C22026" />
          <CardTitle className="text-base text-[#4F4F4F]">مشخصات فنی</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {techArray.fields.map((field, index) => (
            <TechnicalSpecRow
              key={field.id}
              control={control}
              setValue={setValue}
              index={index}
              template={template}
              onRemove={() => techArray.remove(index)}
              keyError={specErrors?.technical_specs?.[index]?.key?.message}
              valueError={specErrors?.technical_specs?.[index]?.value?.message}
            />
          ))}
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="self-start"
            onClick={() => techArray.append({ key: "", value: "" })}
          >
            <Plus set="bold" size={18} primaryColor="#C22026" />
            افزودن مشخصه فنی
          </Button>
        </CardContent>
      </Card>

      <Card className="border-transparent shadow-card">
        <CardHeader className="flex-row items-center gap-2 pb-3">
          <Document set="bulk" size={20} primaryColor="#C22026" />
          <CardTitle className="text-base text-[#4F4F4F]">ویژگی‌ها</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {template.features.map((feature) => {
            const enabled = Boolean(featureToggles[feature.key]);
            const detail = feature.detail;
            const detailFieldError = detail
              ? specErrors?.featureDetails?.[detail.key]
              : undefined;
            const detailMessage =
              typeof detailFieldError === "object" && detailFieldError !== null
                ? detailFieldError.message
                : typeof detailFieldError === "string"
                  ? detailFieldError
                  : undefined;

            return (
              <div
                key={feature.key}
                className="flex flex-col gap-3 rounded-xl bg-[#F7F7F7] p-4 shadow-soft"
              >
                <label className="flex cursor-pointer items-center justify-between gap-3">
                  <span className="text-sm font-bold text-[#4F4F4F]">{feature.label}</span>
                  <Switch
                    checked={enabled}
                    onCheckedChange={(checked) =>
                      setValue(`specifications.featureToggles.${feature.key}`, checked, {
                        shouldDirty: true,
                      })
                    }
                  />
                </label>

                {enabled && detail?.type === "string_array" && (
                  <div className="flex flex-col gap-1.5">
                    <span className="text-xs font-bold text-muted-foreground">{detail.label}</span>
                    <TagInput
                      value={
                        Array.isArray(featureDetails[detail.key])
                          ? (featureDetails[detail.key] as string[])
                          : []
                      }
                      onChange={(tags) =>
                        setValue(`specifications.featureDetails.${detail.key}`, tags, {
                          shouldDirty: true,
                        })
                      }
                      placeholder={detail.placeholder ?? "on/off"}
                      aria-invalid={Boolean(detailMessage)}
                    />
                    {detailMessage && (
                      <p className="text-xs text-destructive">{detailMessage}</p>
                    )}
                  </div>
                )}

                {enabled && detail?.type === "string" && (
                  <div className="flex flex-col gap-1.5">
                    <span className="text-xs font-bold text-muted-foreground">{detail.label}</span>
                    <Input
                      value={
                        typeof featureDetails[detail.key] === "string"
                          ? (featureDetails[detail.key] as string)
                          : ""
                      }
                      onChange={(e) =>
                        setValue(`specifications.featureDetails.${detail.key}`, e.target.value, {
                          shouldDirty: true,
                        })
                      }
                      placeholder={detail.placeholder}
                      aria-invalid={Boolean(detailMessage)}
                    />
                    {detailMessage && (
                      <p className="text-xs text-destructive">{detailMessage}</p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </CardContent>
      </Card>

      <Card className="border-transparent shadow-card">
        <CardHeader className="flex-row items-center gap-2 pb-3">
          <Work set="bulk" size={20} primaryColor="#C22026" />
          <CardTitle className="text-base text-[#4F4F4F]">ابعاد و اندازه‌ها</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {dimArray.fields.map((field, index) => (
            <DimensionRow
              key={field.id}
              control={control}
              register={register}
              setValue={setValue}
              index={index}
              template={template}
              onRemove={() => dimArray.remove(index)}
              keyError={specErrors?.dimensions?.[index]?.key?.message}
              valueError={specErrors?.dimensions?.[index]?.value?.message}
            />
          ))}
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="self-start"
            onClick={() => dimArray.append({ key: "", value: "" })}
          >
            <Plus set="bold" size={18} primaryColor="#C22026" />
            افزودن بعد
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
