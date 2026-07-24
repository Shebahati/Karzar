"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Document, Wallet } from "react-iconly";
import { Button } from "@/components/ui/button";
import { Field, fieldInputClass, fieldTextareaClass } from "@/components/ui/field";
import {
  inquirySchema,
  shippingSchema,
  type InquiryValues,
  type ShippingValues,
} from "@/lib/validation";
import type { ResolvedCustomer } from "@/components/checkout/auth-step";

export interface DetailsResult {
  full_name: string;
  phone: string;
  company_name?: string | null;
  note?: string | null;
  shipping?: {
    province: string;
    city: string;
    postal_code: string;
    address_line: string;
  };
}

/**
 * Step 2 of checkout. Branches on `isInquiry`:
 * - purchase  → full shipping address, primary action "پرداخت".
 * - inquiry   → optional company name, primary action "ثبت استعلام قیمت".
 */
export function DetailsStep({
  isInquiry,
  customer,
  submitting,
  canPay = true,
  onSubmit,
  onBack,
}: {
  isInquiry: boolean;
  customer: ResolvedCustomer | null;
  submitting: boolean;
  canPay?: boolean;
  onSubmit: (result: DetailsResult) => void;
  onBack: () => void;
}) {
  if (isInquiry) {
    return (
      <InquiryForm
        customer={customer}
        submitting={submitting}
        onSubmit={onSubmit}
        onBack={onBack}
      />
    );
  }
  return (
    <ShippingForm
      customer={customer}
      submitting={submitting}
      canPay={canPay}
      onSubmit={onSubmit}
      onBack={onBack}
    />
  );
}

function ShippingForm({
  customer,
  submitting,
  canPay,
  onSubmit,
  onBack,
}: {
  customer: ResolvedCustomer | null;
  submitting: boolean;
  canPay: boolean;
  onSubmit: (r: DetailsResult) => void;
  onBack: () => void;
}) {
  const form = useForm<ShippingValues>({
    resolver: zodResolver(shippingSchema),
    defaultValues: {
      full_name: customer?.full_name ?? "",
      phone: customer?.phone ?? "",
    },
  });
  const { errors } = form.formState;
  const formId = "checkout-shipping-form";

  return (
    <>
      <form
        id={formId}
        onSubmit={form.handleSubmit((v) =>
          onSubmit({
            full_name: v.full_name,
            phone: v.phone,
            note: v.note || null,
            shipping: {
              province: v.province,
              city: v.city,
              postal_code: v.postal_code,
              address_line: v.address_line,
            },
          }),
        )}
        className="rounded-2xl bg-card p-6 shadow-soft sm:p-8"
      >
        <h2 className="text-lg font-bold text-foreground">اطلاعات ارسال</h2>
        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          <Field label="نام و نام خانوادگی" error={errors.full_name?.message}>
            <input {...form.register("full_name")} className={fieldInputClass} />
          </Field>
          <Field label="شماره موبایل" error={errors.phone?.message}>
            <input {...form.register("phone")} inputMode="tel" className={`${fieldInputClass} tnum`} />
          </Field>
          <Field label="استان" error={errors.province?.message}>
            <input {...form.register("province")} className={fieldInputClass} />
          </Field>
          <Field label="شهر" error={errors.city?.message}>
            <input {...form.register("city")} className={fieldInputClass} />
          </Field>
          <Field label="کد پستی" error={errors.postal_code?.message}>
            <input
              {...form.register("postal_code")}
              inputMode="numeric"
              className={`${fieldInputClass} tnum`}
            />
          </Field>
          <Field label="نشانی کامل" error={errors.address_line?.message} className="sm:col-span-2">
            <textarea
              {...form.register("address_line")}
              rows={3}
              className={fieldTextareaClass}
              placeholder="خیابان، کوچه، پلاک، واحد"
            />
          </Field>
          <Field label="توضیحات (اختیاری)" className="sm:col-span-2">
            <textarea {...form.register("note")} rows={2} className={fieldTextareaClass} />
          </Field>
        </div>

        <div className="mt-6 hidden gap-2 lg:flex">
          <Button type="submit" size="lg" className="flex-1 gap-2" disabled={submitting || !canPay}>
            <Wallet set="bold" />
            {submitting ? "در حال ثبت…" : "انتقال به درگاه پرداخت"}
          </Button>
          <Button type="button" variant="muted" size="lg" onClick={onBack}>
            بازگشت
          </Button>
        </div>
        {!canPay && (
          <p className="mt-3 text-sm text-destructive" role="alert">
            برای پرداخت آنلاین ابتدا با کد یک‌بارمصرف وارد شوید.
          </p>
        )}
      </form>

      <div className="mobile-dock flex gap-2 px-4 py-3">
        <Button
          type="submit"
          form={formId}
          size="lg"
          className="flex-1 gap-2"
          disabled={submitting || !canPay}
        >
          <Wallet set="bold" />
          {submitting ? "در حال ثبت…" : "پرداخت"}
        </Button>
        <Button type="button" variant="muted" size="lg" onClick={onBack}>
          بازگشت
        </Button>
      </div>
    </>
  );
}

function InquiryForm({
  customer,
  submitting,
  onSubmit,
  onBack,
}: {
  customer: ResolvedCustomer | null;
  submitting: boolean;
  onSubmit: (r: DetailsResult) => void;
  onBack: () => void;
}) {
  const form = useForm<InquiryValues>({
    resolver: zodResolver(inquirySchema),
    defaultValues: {
      full_name: customer?.full_name ?? "",
      phone: customer?.phone ?? "",
    },
  });
  const { errors } = form.formState;
  const formId = "checkout-inquiry-form";

  return (
    <>
      <form
        id={formId}
        onSubmit={form.handleSubmit((v) =>
          onSubmit({
            full_name: v.full_name,
            phone: v.phone,
            company_name: v.company_name || null,
            note: v.note || null,
          }),
        )}
        className="rounded-2xl bg-card p-6 shadow-soft sm:p-8"
      >
        <h2 className="text-lg font-bold text-foreground">اطلاعات استعلام</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          کارشناسان ما پس از بررسی، پیش‌فاکتور را برای شما ارسال می‌کنند.
        </p>
        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          <Field label="نام و نام خانوادگی" error={errors.full_name?.message}>
            <input {...form.register("full_name")} className={fieldInputClass} />
          </Field>
          <Field label="شماره موبایل" error={errors.phone?.message}>
            <input {...form.register("phone")} inputMode="tel" className={`${fieldInputClass} tnum`} />
          </Field>
          <Field
            label="نام شرکت (اختیاری)"
            hint="برای خریدهای سازمانی و صدور فاکتور رسمی"
            className="sm:col-span-2"
          >
            <input {...form.register("company_name")} className={fieldInputClass} />
          </Field>
          <Field label="توضیحات درخواست (اختیاری)" className="sm:col-span-2">
            <textarea
              {...form.register("note")}
              rows={3}
              className={fieldTextareaClass}
              placeholder="تعداد مورد نیاز، زمان تحویل، یا توضیحات فنی"
            />
          </Field>
        </div>

        <div className="mt-6 hidden gap-2 lg:flex">
          <Button type="submit" size="lg" className="flex-1 gap-2" disabled={submitting}>
            <Document set="bold" />
            {submitting ? "در حال ثبت…" : "ثبت استعلام قیمت"}
          </Button>
          <Button type="button" variant="muted" size="lg" onClick={onBack}>
            بازگشت
          </Button>
        </div>
      </form>

      <div className="mobile-dock flex gap-2 px-4 py-3">
        <Button type="submit" form={formId} size="lg" className="flex-1 gap-2" disabled={submitting}>
          <Document set="bold" />
          {submitting ? "در حال ثبت…" : "ثبت استعلام"}
        </Button>
        <Button type="button" variant="muted" size="lg" onClick={onBack}>
          بازگشت
        </Button>
      </div>
    </>
  );
}
