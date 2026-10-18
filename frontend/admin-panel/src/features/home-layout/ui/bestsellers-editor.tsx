"use client";

import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/api-client";
import { useProducts, useProductsByIds } from "@/features/catalog/queries";

type Selection = { product_ids: number[]; revision: number; published_at: string | null };
const MAX_ITEMS = 24;
const available = (p: { availability: boolean; stock_status: string }) =>
  p.availability === true && (p.stock_status === "in_stock" || p.stock_status === "موجود");

export function BestsellersEditor() {
  const [selection, setSelection] = useState<Selection | null>(null);
  const [ids, setIds] = useState<number[]>([]);
  const [search, setSearch] = useState("");
  const [publishing, setPublishing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [dirty, setDirty] = useState(false);
  const productsQuery = useProducts({ search: search.trim() || undefined, limit: 48 });
  const selected = useProductsByIds(ids);
  const byId = useMemo(() => new Map((selected.data ?? []).map(p => [p.id, p])), [selected.data]);

  async function reload() {
    setLoading(true);
    try {
      const { data } = await apiClient.get<Selection>("/home/bestsellers");
      setSelection(data);
      setIds(data.product_ids);
      setDirty(false);
    } catch {
      toast.error("دریافت انتخاب پرفروش‌ها ناموفق بود؛ چیزی منتشر نشد.");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { void reload(); }, []);
  function patch(next: number[]) { setIds(next); setDirty(true); }
  function toggle(id: number) {
    if (ids.includes(id)) return patch(ids.filter(x => x !== id));
    if (ids.length >= MAX_ITEMS) { toast.error("حداکثر ۲۴ محصول قابل انتخاب است."); return; }
    patch([...ids, id]);
  }
  function move(index: number, delta: -1 | 1) {
    const other = index + delta;
    if (other < 0 || other >= ids.length) return;
    const next = [...ids];
    [next[index], next[other]] = [next[other]!, next[index]!];
    patch(next);
  }
  async function publish() {
    if (!selection || publishing) return;
    setPublishing(true);
    try {
      const { data } = await apiClient.put<Selection>("/home/bestsellers", {
        product_ids: ids, expected_revision: selection.revision,
      });
      setSelection(data);
      setIds(data.product_ids);
      setDirty(false);
      toast.success("فهرست انتخابی پرفروش‌ها در دیتابیس منتشر شد.");
    } catch {
      toast.error("انتشار ناموفق: ممکن است محصول ناموجود شده یا نسخهٔ جدیدتری ثبت شده باشد. فهرست را مجدداً بارگذاری کنید.");
    } finally {
      setPublishing(false);
    }
  }
  return (
    <div className="mt-4 space-y-4 rounded-lg border border-border/60 bg-white p-4">
      <p className="text-sm text-muted-foreground">
        پرفروش‌های این بخش را شما دستی انتخاب می‌کنید؛ این فهرست آمار فروش نیست.
        ترتیب نمایش قابل تغییر است. انتشار از طریق API و دیتابیس انجام می‌شود، نه فایل چیدمان در کانتینر.
        محصولی که بعداً ناموجود شود، خودکار از نمایش حذف می‌شود.
      </p>
      {loading || !selection ? (
        <p className="text-sm text-muted-foreground">در حال دریافت فهرست منتشرشده…</p>
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-sm font-semibold">{ids.length.toLocaleString("fa-IR")} محصول از {MAX_ITEMS.toLocaleString("fa-IR")}</span>
            <span className="text-xs text-muted-foreground">نسخه {selection.revision.toLocaleString("fa-IR")}{dirty ? " · تغییرات منتشرنشده" : ""}</span>
          </div>
          <ol className="space-y-2">
            {ids.map((id, index) => {
              const p = byId.get(id);
              return (
                <li key={id} className="flex flex-wrap items-center gap-2 rounded-lg border p-2 text-sm">
                  <span className="w-6 shrink-0 tabular-nums">{(index + 1).toLocaleString("fa-IR")}</span>
                  <span className="min-w-0 flex-1 truncate">{p ? [p.name, p.sku].join(" · ") : "محصول #" + id + " (اطلاعات در دسترس نیست)"}</span>
                  {p && !available(p) ? <span className="text-xs text-destructive">ناموجود؛ در سایت پنهان می‌شود</span> : null}
                  <Button type="button" size="sm" variant="outline" disabled={index === 0} onClick={() => move(index, -1)}>↑</Button>
                  <Button type="button" size="sm" variant="outline" disabled={index === ids.length - 1} onClick={() => move(index, 1)}>↓</Button>
                  <Button type="button" size="sm" variant="ghost" onClick={() => toggle(id)}>حذف</Button>
                </li>
              );
            })}
          </ol>
          <label className="block text-sm font-medium">جست‌وجوی محصول با نام، کد کالا یا برند
            <Input className="mt-2" value={search} onChange={e => setSearch(e.target.value)} placeholder="نام یا SKU"/>
          </label>
          {productsQuery.isLoading ? <p className="text-sm">در حال دریافت محصولات…</p> : (
            <div className="max-h-56 space-y-1 overflow-y-auto rounded-md border p-2">
              {(productsQuery.data?.data ?? []).filter(available).map(p => (
                <button type="button" key={p.id} disabled={!ids.includes(p.id) && ids.length >= MAX_ITEMS}
                  onClick={() => toggle(p.id)}
                  className="flex w-full items-center justify-between gap-3 rounded-md p-2 text-right text-sm hover:bg-muted disabled:opacity-40">
                  <span className="min-w-0 truncate">{[p.name, p.sku].join(" · ")}</span>
                  <span className="shrink-0 font-medium">{ids.includes(p.id) ? "انتخاب‌شده ✓" : "افزودن +"}</span>
                </button>
              ))}
            </div>
          )}
          <div className="flex flex-wrap gap-2">
            <Button type="button" disabled={!dirty || publishing} onClick={() => void publish()}>{publishing ? "در حال انتشار…" : "انتشار انتخاب پرفروش‌ها"}</Button>
            <Button type="button" variant="outline" disabled={publishing} onClick={() => void reload()}>بارگذاری مجدد</Button>
          </div>
        </>
      )}
    </div>
  );
}
