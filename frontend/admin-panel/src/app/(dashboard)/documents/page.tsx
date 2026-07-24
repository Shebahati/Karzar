export default function DocumentsPage() {
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div>
        <h2 className="text-2xl font-bold text-foreground">اسناد</h2>
        <p className="mt-1 text-sm text-muted-foreground">آرشیو اسناد و کاتالوگ‌های فروشگاه</p>
      </div>

      <div className="rounded-2xl border border-border/60 bg-card p-10 text-center shadow-sm">
        <p className="inline-block rounded-full border border-border px-3 py-1 text-xs font-bold text-muted-foreground">
          به‌زودی
        </p>
        <p className="mt-4 text-base font-bold text-foreground">
          مدیریت اسناد هنوز به backend متصل نشده است
        </p>
        <p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-muted-foreground">
          آپلود، دانلود و آرشیو اسناد پس از اتصال این بخش به سرویس واقعی فعال می‌شود. در حال حاضر
          هیچ فایلی ذخیره یا بازیابی نمی‌گردد.
        </p>
      </div>
    </div>
  );
}
