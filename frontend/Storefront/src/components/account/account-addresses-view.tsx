"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Delete, Edit, Location, Plus, Star } from "react-iconly";
import { Container } from "@/components/ui/container";
import { Button } from "@/components/ui/button";
import { Field, fieldInputClass, fieldTextareaClass } from "@/components/ui/field";
import { isLoggedIn } from "@/lib/api-client";
import { cn, toPersianDigits } from "@/lib/utils";
import {
  useAddressStore,
  type AddressInput,
  type SavedAddress,
} from "@/store/address-store";

const EMPTY: AddressInput = {
  label: "",
  full_name: "",
  phone: "",
  province: "",
  city: "",
  postal_code: "",
  address_line: "",
  is_default: false,
};

export function AccountAddressesView() {
  const router = useRouter();
  const addresses = useAddressStore((s) => s.addresses);
  const addAddress = useAddressStore((s) => s.addAddress);
  const updateAddress = useAddressStore((s) => s.updateAddress);
  const removeAddress = useAddressStore((s) => s.removeAddress);
  const setDefault = useAddressStore((s) => s.setDefault);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState<AddressInput>(EMPTY);
  const [openForm, setOpenForm] = useState(false);

  useEffect(() => {
    if (!isLoggedIn()) router.replace("/login?next=/account/addresses");
  }, [router]);

  if (!isLoggedIn()) {
    return (
      <Container className="py-16">
        <p className="text-center text-sm text-steel">در حال هدایت به ورود…</p>
      </Container>
    );
  }

  const startCreate = () => {
    setEditingId(null);
    setDraft({ ...EMPTY, is_default: addresses.length === 0 });
    setOpenForm(true);
  };

  const startEdit = (addr: SavedAddress) => {
    setEditingId(addr.id);
    setDraft({
      label: addr.label,
      full_name: addr.full_name,
      phone: addr.phone,
      province: addr.province,
      city: addr.city,
      postal_code: addr.postal_code,
      address_line: addr.address_line,
      is_default: addr.is_default,
    });
    setOpenForm(true);
  };

  const save = () => {
    if (
      !draft.full_name.trim() ||
      !draft.phone.trim() ||
      !draft.province.trim() ||
      !draft.city.trim() ||
      !draft.postal_code.trim() ||
      !draft.address_line.trim()
    ) {
      return;
    }
    if (editingId) {
      updateAddress(editingId, draft);
      if (draft.is_default) setDefault(editingId);
    } else {
      addAddress(draft);
    }
    setOpenForm(false);
    setEditingId(null);
    setDraft(EMPTY);
  };

  return (
    <Container className="py-8 lg:py-12">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Link href="/account" className="text-sm text-primary">
            ← حساب کاربری
          </Link>
          <h1 className="mt-2 text-2xl font-bold text-foreground">آدرس‌های من</h1>
          <p className="mt-1 text-sm text-steel">
            آدرس‌های ذخیره‌شده برای ارسال سریع در تسویه‌حساب
          </p>
        </div>
        <Button className="gap-2" onClick={startCreate}>
          <Plus set="bold" />
          آدرس جدید
        </Button>
      </div>

      {openForm && (
        <div className="mt-6 rounded-2xl border border-border/50 bg-card p-5 shadow-soft sm:p-6">
          <h2 className="text-base font-bold text-foreground">
            {editingId ? "ویرایش آدرس" : "ثبت آدرس جدید"}
          </h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <Field label="برچسب (مثلاً خانه)">
              <input
                value={draft.label}
                onChange={(e) => setDraft((d) => ({ ...d, label: e.target.value }))}
                className={fieldInputClass}
                placeholder="خانه / محل کار"
              />
            </Field>
            <Field label="نام گیرنده">
              <input
                value={draft.full_name}
                onChange={(e) => setDraft((d) => ({ ...d, full_name: e.target.value }))}
                className={fieldInputClass}
              />
            </Field>
            <Field label="موبایل">
              <input
                value={draft.phone}
                onChange={(e) => setDraft((d) => ({ ...d, phone: e.target.value }))}
                inputMode="tel"
                className={`${fieldInputClass} tnum`}
              />
            </Field>
            <Field label="کد پستی">
              <input
                value={draft.postal_code}
                onChange={(e) => setDraft((d) => ({ ...d, postal_code: e.target.value }))}
                inputMode="numeric"
                className={`${fieldInputClass} tnum`}
              />
            </Field>
            <Field label="استان">
              <input
                value={draft.province}
                onChange={(e) => setDraft((d) => ({ ...d, province: e.target.value }))}
                className={fieldInputClass}
              />
            </Field>
            <Field label="شهر">
              <input
                value={draft.city}
                onChange={(e) => setDraft((d) => ({ ...d, city: e.target.value }))}
                className={fieldInputClass}
              />
            </Field>
            <Field label="نشانی کامل" className="sm:col-span-2">
              <textarea
                value={draft.address_line}
                onChange={(e) => setDraft((d) => ({ ...d, address_line: e.target.value }))}
                rows={3}
                className={fieldTextareaClass}
              />
            </Field>
            <label className="flex min-h-11 items-center gap-2 text-sm sm:col-span-2">
              <input
                type="checkbox"
                checked={Boolean(draft.is_default)}
                onChange={(e) =>
                  setDraft((d) => ({ ...d, is_default: e.target.checked }))
                }
                className="h-4 w-4 accent-primary"
              />
              تنظیم به‌عنوان آدرس پیش‌فرض
            </label>
          </div>
          <div className="mt-5 flex flex-wrap gap-2">
            <Button onClick={save}>{editingId ? "ذخیره تغییرات" : "افزودن آدرس"}</Button>
            <Button
              variant="muted"
              onClick={() => {
                setOpenForm(false);
                setEditingId(null);
              }}
            >
              انصراف
            </Button>
          </div>
        </div>
      )}

      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        {addresses.length === 0 && !openForm ? (
          <div className="col-span-full grid place-items-center rounded-2xl bg-card py-16 text-center shadow-soft">
            <span className="grid h-14 w-14 place-items-center rounded-2xl bg-secondary text-steel">
              <Location set="bold" />
            </span>
            <p className="mt-4 font-bold text-foreground">هنوز آدرسی ذخیره نشده</p>
            <p className="mt-1 text-sm text-steel">اولین آدرس ارسال خود را اضافه کنید.</p>
            <Button className="mt-5 gap-2" onClick={startCreate}>
              <Plus set="bold" />
              افزودن آدرس
            </Button>
          </div>
        ) : (
          addresses.map((addr) => (
            <article
              key={addr.id}
              className={cn(
                "relative rounded-2xl border bg-card p-5 shadow-soft",
                addr.is_default ? "border-primary/40" : "border-border/40",
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-bold text-foreground">{addr.label}</h3>
                    {addr.is_default && (
                      <span className="inline-flex items-center gap-1 rounded-md bg-accent px-2 py-0.5 text-[10px] font-bold text-primary">
                        <Star set="bold" size="small" />
                        پیش‌فرض
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-sm text-foreground">{addr.full_name}</p>
                  <p className="mt-0.5 text-xs text-steel tnum">{toPersianDigits(addr.phone)}</p>
                </div>
              </div>
              <p className="mt-3 text-sm leading-6 text-foreground/80">
                {addr.province}، {addr.city}
                <br />
                {addr.address_line}
                <br />
                <span className="tnum text-steel">کد پستی {toPersianDigits(addr.postal_code)}</span>
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                {!addr.is_default && (
                  <Button variant="soft" size="sm" onClick={() => setDefault(addr.id)}>
                    پیش‌فرض
                  </Button>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1"
                  onClick={() => startEdit(addr)}
                >
                  <Edit set="light" size="small" />
                  ویرایش
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="gap-1 text-destructive"
                  onClick={() => {
                    if (window.confirm("این آدرس حذف شود؟")) removeAddress(addr.id);
                  }}
                >
                  <Delete set="light" size="small" />
                  حذف
                </Button>
              </div>
            </article>
          ))
        )}
      </div>
    </Container>
  );
}
