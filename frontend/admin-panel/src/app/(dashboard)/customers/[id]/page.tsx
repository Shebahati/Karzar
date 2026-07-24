"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowRight, Delete } from "react-iconly";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { TagInput } from "@/components/ui/tag-input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { StepUpDialog } from "@/components/step-up-dialog";
import { CustomerOrdersSection } from "@/features/customers/components/customer-orders-section";
import { useCustomer, useDeleteCustomer, useUpdateCustomer } from "@/features/customers/queries";
import { ApiError } from "@/lib/api-client";
import { formatNumber, toPersianDigits } from "@/lib/utils";
import { CUSTOMER_CATEGORIES } from "@/types/customer";

function useSyncedState<T>(value: T) {
  const [state, setState] = useState(value);
  useEffect(() => {
    setState(value);
  }, [value]);
  return [state, setState] as const;
}

export default function CustomerDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = Number(params.id);

  const { data: customer, isPending } = useCustomer(id);
  const updateCustomer = useUpdateCustomer(id);
  const deleteCustomer = useDeleteCustomer();

  const [fullName, setFullName] = useSyncedState(customer?.full_name ?? "");
  const [isActive, setIsActive] = useSyncedState(customer?.is_active ?? true);
  const [note, setNote] = useSyncedState(customer?.note ?? "");
  const [category, setCategory] = useSyncedState(customer?.category ?? "");
  const [tags, setTags] = useSyncedState<string[]>(customer?.tags ?? []);
  const [showStepUp, setShowStepUp] = useState(false);
  const [showDeleteStepUp, setShowDeleteStepUp] = useState(false);

  function handleDeleteVerified(stepUpToken: string) {
    deleteCustomer.mutate(
      { id, stepUpToken },
      {
        onSuccess: () => {
          toast.success("حساب مشتری حذف شد");
          setShowDeleteStepUp(false);
          router.push("/customers");
        },
        onError: (err) => {
          toast.error(err instanceof ApiError ? err.message : "حذف مشتری ناموفق بود");
        },
      },
    );
  }

  async function saveChanges(stepUpToken?: string) {
    try {
      await updateCustomer.mutateAsync({
        full_name: fullName.trim() || null,
        is_active: isActive,
        note: note.trim() || null,
        category: category || null,
        tags,
        stepUpToken,
      });
      toast.success("اطلاعات مشتری ذخیره شد");
      setShowStepUp(false);
    } catch (err) {
      if (err instanceof ApiError && err.code === "STEP_UP_REQUIRED") {
        setShowStepUp(true);
        return;
      }
      toast.error(err instanceof ApiError ? err.message : "ذخیره ناموفق بود");
    }
  }

  if (isPending) {
    return (
      <div className="mx-auto max-w-4xl space-y-4 px-1">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!customer) {
    return <p className="p-8 text-center text-sm">مشتری یافت نشد.</p>;
  }

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-5 px-1 sm:gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <Button asChild variant="ghost" size="icon" className="mt-0.5">
            <Link href="/customers" aria-label="بازگشت">
              <ArrowRight set="light" size={22} />
            </Link>
          </Button>
          <div>
            <h2 className="text-xl font-bold text-foreground sm:text-2xl">
              {customer.full_name ?? "بدون نام"}
            </h2>
            <p className="text-sm text-muted-foreground tnum">{toPersianDigits(customer.phone)}</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {customer.category && <Badge>{customer.category}</Badge>}
              {customer.tags.map((tag) => (
                <Badge key={tag} variant="outline">
                  {tag}
                </Badge>
              ))}
            </div>
          </div>
        </div>
        <div className="rounded-xl bg-muted/60 px-4 py-3 text-center text-sm">
          <p className="font-bold tnum">{formatNumber(customer.order_count)}</p>
          <p className="text-xs text-muted-foreground">سفارش</p>
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
        <CustomerOrdersSection phone={customer.phone} />

        <div className="flex flex-col gap-5">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">پروفایل مشتری</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              <Field label="نام و نام خانوادگی" htmlFor="full_name">
                <Input id="full_name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
              </Field>

              <Field label="دسته‌بندی مشتری" htmlFor="category">
                <Select value={category || "none"} onValueChange={(v) => setCategory(v === "none" ? "" : v)}>
                  <SelectTrigger id="category">
                    <SelectValue placeholder="انتخاب دسته" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">بدون دسته</SelectItem>
                    {CUSTOMER_CATEGORIES.map((cat) => (
                      <SelectItem key={cat} value={cat}>
                        {cat}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>

              <Field label="برچسب‌ها" htmlFor="tags">
                <TagInput value={tags} onChange={setTags} placeholder="برچسب بنویسید و Enter بزنید" />
              </Field>

              <Field label="یادداشت داخلی" htmlFor="note">
                <Textarea
                  id="note"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  rows={3}
                  placeholder="ترجیحات، تاریخچه همکاری، ..."
                />
              </Field>

              <label className="flex items-center justify-between gap-4 rounded-lg bg-muted/50 px-4 py-3">
                <span className="text-sm font-bold">حساب فعال</span>
                <Switch checked={isActive} onCheckedChange={setIsActive} />
              </label>

              <Button onClick={() => void saveChanges()} disabled={updateCustomer.isPending} className="w-full">
                {updateCustomer.isPending ? "در حال ذخیره…" : "ذخیره تغییرات"}
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="space-y-2 p-5 text-sm">
              <p>
                <span className="text-muted-foreground">تاریخ عضویت: </span>
                {new Date(customer.created_at).toLocaleDateString("fa-IR")}
              </p>
              {customer.email && (
                <p dir="ltr" className="text-start tnum">
                  {customer.email}
                </p>
              )}
            </CardContent>
          </Card>

          <Card className="border-destructive/20">
            <CardHeader>
              <CardTitle className="text-base text-destructive">منطقه حساس</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-xs leading-6 text-muted-foreground">
                حذف حساب مشتری غیرقابل بازگشت است و نیاز به تأیید کد PIN امنیتی دارد.
              </p>
              <Button
                type="button"
                variant="outline"
                className="w-full gap-2 border-destructive/30 text-destructive hover:bg-destructive/5"
                onClick={() => setShowDeleteStepUp(true)}
              >
                <Delete set="light" size={18} primaryColor="currentColor" />
                حذف حساب مشتری
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>

      <StepUpDialog
        open={showStepUp}
        onOpenChange={setShowStepUp}
        title="تأیید هویت"
        description="ویرایش مشتری نیاز به کد PIN امنیتی دارد."
        onVerified={(token) => void saveChanges(token)}
      />

      <StepUpDialog
        open={showDeleteStepUp}
        onOpenChange={setShowDeleteStepUp}
        title="حذف حساب مشتری"
        description={`برای حذف حساب «${customer.full_name ?? customer.phone}» کد امنیتی مدیر را وارد کنید.`}
        actionPending={deleteCustomer.isPending}
        onVerified={handleDeleteVerified}
      />
    </div>
  );
}
