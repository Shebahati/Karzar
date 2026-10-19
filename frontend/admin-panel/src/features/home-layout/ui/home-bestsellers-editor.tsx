"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";
import { apiClient } from "@/lib/api-client";
import { useProductsByIds } from "@/features/catalog/queries";
import { catalogService } from "@/services/catalog";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { isCuratedAvailable } from "./home-bestsellers-availability";
import type { ProductSummary } from "@/types/product";

type Selection = { product_ids: number[]; revision: number; published_at: string | null };
const URL = "/home-merchandising/bestsellers";
export function HomeBestsellersEditor() {
  const [saved, setSaved] = useState<Selection | null>(null);
  const [ids, setIds] = useState<number[]>([]);
  const [search, setSearch] = useState("");
  const [matches, setMatches] = useState<ProductSummary[]>([]);
  const [busy, setBusy] = useState(false);
  const [searching, setSearching] = useState(false);
  const selected = useProductsByIds(ids);
  const selectedById = new Map((selected.data ?? []).map(p => [p.id, p]));
  const changed = saved !== null && JSON.stringify(ids) !== JSON.stringify(saved.product_ids);
  useEffect(() => {
    let live = true;
    apiClient.get<Selection>(URL).then(({ data }) => {
      if (live) { setSaved(data); setIds(data.product_ids); }
    }).catch(() => { if (live) toast.error("بارگذاری انتخاب پرفروش‌ها ناموفق بود"); });
    return () => { live = false; };
  }, []);
  useEffect(() => {
    let live = true;
    if (search.trim().length < 2) { setMatches([]); return; }
    setSearching(true);
    const timer = setTimeout(() => {
      catalogService.listProducts({ search: search.trim(), limit: 30, is_active: true })
        .then(result => { if (live) setMatches(result.data.filter(isCuratedAvailable)); })
        .catch(() => { if (live) setMatches([]); })
        .finally(() => { if (live) setSearching(false); });
    }, 300);
    return () => { live = false; clearTimeout(timer); };
  }, [search]);
  function move(index: number, direction: number) {
    const next = index + direction;
    if (next < 0 || next >= ids.length) return;
    setIds(prev => { const copy = [...prev]; [copy[index], copy[next]] = [copy[next]!, copy[index]!]; return copy; });
  }
  async function publish() {
    if (!saved || busy || !changed) return;
    if (ids.some(id => !selectedById.has(id) || !isCuratedAvailable(selectedById.get(id)!))) {
      toast.error("بعضی کالاها ناموجود یا از کاتالوگ عمومی حذف شده‌اند؛ ابتدا آن‌ها را حذف کنید.");
      return;
    }
    setBusy(true);
    try {
      const { data } = await apiClient.put<Selection>(URL, { product_ids: ids, expected_revision: saved.revision });
      setSaved(data); setIds(data.product_ids);
      toast.success("فهرست انتخابی پرفروش‌ها در دیتابیس منتشر شد");
    } catch (error) {
      toast.error("انتشار ناموفق بود یا نسخهٔ دیگری ثبت شده است؛ صفحه را تازه‌سازی کنید");
    } finally { setBusy(false); }
  }
  return <Card><CardContent className="space-y-4 p-4">
    <div><h3 className="font-bold">انتخاب دستی پرفروش‌ها</h3>
      <p className="text-sm text-muted-foreground">از ۰ تا ۴۸ محصول؛ ترتیب نمایش دقیقاً همین ترتیب است. محصول ناموجود نمایش داده نمی‌شود. این انتشار مستقل از چیدمان هوم و پس از دیپلوی محفوظ است.</p></div>
    <div className="flex flex-wrap items-center gap-3"><span>تعداد انتخاب: {ids.length.toLocaleString("fa-IR")} از ۴۸</span>
      <Button type="button" disabled={!changed || busy || !saved || selected.isLoading} onClick={() => void publish()}>{busy ? "در حال انتشار..." : "انتشار پرفروش‌ها"}</Button>
      <Button type="button" variant="outline" disabled={!changed || busy} onClick={() => setIds(saved?.product_ids ?? [])}>انصراف از تغییرات</Button>
    </div>
    {saved === null ? <p role="status">بارگذاری تنظیمات...</p> : null}
    <Input aria-label="جست‌وجوی محصولات پرفروش" placeholder="جست‌وجو با نام یا SKU (حداقل دو حرف)" value={search} onChange={e => setSearch(e.target.value)} />
    {searching ? <p role="status">در حال جست‌وجو...</p> : null}
    {matches.length ? <div className="max-h-52 space-y-1 overflow-y-auto border p-2" aria-label="نتایج جست‌وجو">{matches.map(p => <div key={p.id} className="flex items-center justify-between gap-2 text-sm"><span>{p.name} · {p.sku} · #{p.id}</span><Button type="button" variant="outline" size="sm" disabled={ids.includes(p.id) || ids.length >= 48} onClick={() => { setIds(prev => [...prev, p.id]); setSearch(""); setMatches([]); }}>افزودن</Button></div>)}</div> : null}
    <div className="space-y-2">{ids.map((id, i) => { const p = selectedById.get(id); const valid = p && isCuratedAvailable(p); return <div key={id} className="flex flex-wrap items-center gap-2 rounded border p-2 text-sm"><span className="w-8">{i + 1}.</span><span className="min-w-0 flex-1">{p ? `${p.name} · ${p.sku}` : `شناسه #${id} (در حال بررسی یا حذف‌شده)`}</span>{!valid && !selected.isLoading ? <span className="text-red-600">ناموجود یا غیرقابل‌نمایش</span> : null}<Button type="button" variant="outline" size="sm" disabled={i === 0} onClick={() => move(i, -1)}>بالا</Button><Button type="button" variant="outline" size="sm" disabled={i === ids.length - 1} onClick={() => move(i, 1)}>پایین</Button><Button type="button" variant="outline" size="sm" onClick={() => setIds(prev => prev.filter(x => x !== id))}>حذف</Button></div>; })}</div>
    {ids.length === 0 ? <p className="text-sm text-muted-foreground">فهرست خالی است؛ تا زمان انتشار انتخاب شما، کاروسل پرفروش‌ها مخفی می‌ماند.</p> : null}
  </CardContent></Card>;
}
