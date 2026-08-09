"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Delete, Document, Plus } from "react-iconly";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { CatalogProductPicker } from "@/features/invoices/components/catalog-product-picker";
import { useCreateIssuedProforma } from "@/features/invoices/queries";
import { downloadAdminInvoicePdf } from "@/lib/invoice-pdf";
import { formatNumber, formatToman, toEnglishDigits } from "@/lib/utils";
import {
  documentGrandTotalToman,
  lineDiscountToman,
  lineGrossToman,
  lineNetToman,
  makeLocalRefCode,
} from "@/services/issued-proformas";
import type {
  InvoiceBuyerInput,
  InvoiceDocKind,
  InvoiceDocumentPayload,
  InvoiceLineInput,
} from "@/types/invoice-doc";
import type { ProductSummary } from "@/types/product";

function emptyBuyer(): InvoiceBuyerInput {
  return {
    fullName: "",
    companyName: "",
    phone: "",
    mobile: "",
    address: "",
    postalCode: "",
    nationalId: "",
  };
}

function emptyLine(): InvoiceLineInput {
  return {
    productId: null,
    name: "",
    sku: "",
    quantity: 1,
    unitPriceToman: 0,
    discountAmountToman: 0,
    discountPercent: 0,
  };
}

function parseMoney(raw: string): number {
  const n = Number(toEnglishDigits(raw).replace(/,/g, "").trim());
  return Number.isFinite(n) && n >= 0 ? n : 0;
}

function parseQty(raw: string): number {
  const n = Number(toEnglishDigits(raw).replace(/,/g, "").trim());
  if (!Number.isFinite(n) || n <= 0) return 1;
  return Math.floor(n);
}

export function InvoiceBuilder() {
  const [kind, setKind] = useState<InvoiceDocKind>("proforma");
  const [buyer, setBuyer] = useState<InvoiceBuyerInput>(emptyBuyer);
  const [lines, setLines] = useState<InvoiceLineInput[]>([emptyLine()]);
  const [adminNote, setAdminNote] = useState("");
  const [pickerOpen, setPickerOpen] = useState(false);
  const [pickerTarget, setPickerTarget] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const createIssued = useCreateIssuedProforma();

  const grandToman = useMemo(
    () => documentGrandTotalToman({ kind, refCode: "", createdAt: "", buyer, lines }),
    [buyer, kind, lines],
  );

  function updateLine(index: number, patch: Partial<InvoiceLineInput>) {
    setLines((prev) =>
      prev.map((row, i) => (i === index ? { ...row, ...patch } : row)),
    );
  }

  function applyProduct(index: number, product: ProductSummary) {
    const unit = Number(product.base_price);
    updateLine(index, {
      productId: product.id,
      name: product.name,
      sku: product.sku,
      unitPriceToman: Number.isFinite(unit) && unit >= 0 ? unit : 0,
      discountPercent: 0,
      discountAmountToman: 0,
    });
  }

  function openPicker(index: number) {
    setPickerTarget(index);
    setPickerOpen(true);
  }

  async function handleGenerate() {
    const validLines = lines.filter((l) => l.name.trim() && l.quantity > 0);
    if (!validLines.length) {
      toast.error("حداقل یک ردیف کالا با نام وارد کنید");
      return;
    }
    if (!buyer.fullName.trim() && !buyer.companyName.trim()) {
      toast.error("نام خریدار یا شرکت را وارد کنید");
      return;
    }
    if (kind === "invoice") {
      if (!buyer.address.trim() || !(buyer.postalCode ?? "").trim()) {
        toast.error("برای فاکتور، آدرس و کد پستی خریدار الزامی است");
        return;
      }
    }

    const document: InvoiceDocumentPayload = {
      kind,
      refCode: makeLocalRefCode(kind),
      createdAt: new Date().toISOString(),
      buyer: {
        ...buyer,
        fullName: buyer.fullName.trim(),
        companyName: buyer.companyName.trim(),
        phone: buyer.phone.trim(),
        mobile: buyer.mobile.trim(),
        address: buyer.address.trim(),
        postalCode: (buyer.postalCode ?? "").trim(),
        nationalId: buyer.nationalId.trim(),
      },
      lines: validLines.map((l) => ({
        ...l,
        name: l.name.trim(),
        sku: l.sku.trim(),
        quantity: Math.max(1, Math.floor(l.quantity)),
        unitPriceToman: Math.max(0, l.unitPriceToman),
        discountAmountToman: Math.max(0, l.discountAmountToman),
        discountPercent: Math.min(100, Math.max(0, l.discountPercent)),
      })),
      adminNote: adminNote.trim() || undefined,
    };

    setBusy(true);
    try {
      await downloadAdminInvoicePdf(document);
      if (kind === "proforma") {
        await createIssued.mutateAsync({
          document,
          source: "invoice-builder",
        });
        toast.success("پیش‌فاکتور تولید شد و در فهرست محلی ثبت شد");
      } else {
        toast.success("فاکتور برای چاپ / ذخیره PDF باز شد");
      }
    } catch (err) {
      const code = err instanceof Error ? err.message : "";
      if (code === "POPUP_BLOCKED") {
        toast.error("پنجره پاپ‌آپ مسدود است — اجازه را در مرورگر فعال کنید");
      } else if (code === "MISSING_BUYER_ADDRESS") {
        toast.error("برای فاکتور، آدرس و کد پستی خریدار الزامی است");
      } else {
        toast.error("خطا در تولید سند");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-[#4F4F4F]">فاکتورساز</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            تولید فاکتور یا پیش‌فاکتور به‌صورت محلی (دانلود PDF). چیزی در پایگاه‌داده
            سرور ذخیره نمی‌شود. پیش‌فاکتورها فقط در همین مرورگر (localStorage) ثبت
            می‌شوند تا وقتی API آماده شود.
          </p>
        </div>
        <Button asChild variant="outline" size="sm">
          <Link href="/finance/issued-proformas">پیش‌فاکتورهای صادر شده</Link>
        </Button>
      </div>

      <Card className="border-transparent shadow-sm">
        <CardContent className="flex flex-wrap items-center justify-between gap-4 p-5">
          <div className="flex items-center gap-3">
            <Switch
              id="doc-kind"
              checked={kind === "proforma"}
              onCheckedChange={(on) => setKind(on ? "proforma" : "invoice")}
              aria-label="نوع سند"
            />
            <div>
              <Label htmlFor="doc-kind" className="text-sm font-bold text-[#4F4F4F]">
                {kind === "proforma" ? "پیش‌فاکتور" : "فاکتور"}
              </Label>
              <p className="text-xs text-muted-foreground">
                {kind === "proforma"
                  ? "با بلوک پرداخت و اعتبار ۲۴ ساعته"
                  : "سند فروش بدون بلوک واریز پیش‌فاکتور"}
              </p>
            </div>
          </div>
          <Badge variant="neutral" className="tnum">
            جمع کل: {formatToman(grandToman)}
          </Badge>
        </CardContent>
      </Card>

      <Card className="border-transparent shadow-sm">
        <CardContent className="space-y-4 p-5">
          <h3 className="text-sm font-bold text-[#4F4F4F]">مشخصات خریدار</h3>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div className="space-y-1.5">
              <Label>نام و نام خانوادگی</Label>
              <Input
                value={buyer.fullName}
                onChange={(e) => setBuyer((b) => ({ ...b, fullName: e.target.value }))}
                placeholder="مثلاً علی رضایی"
              />
            </div>
            <div className="space-y-1.5">
              <Label>نام شرکت (اختیاری)</Label>
              <Input
                value={buyer.companyName}
                onChange={(e) =>
                  setBuyer((b) => ({ ...b, companyName: e.target.value }))
                }
                placeholder="در صورت خرید سازمانی"
              />
            </div>
            <div className="space-y-1.5">
              <Label>تلفن</Label>
              <Input
                value={buyer.phone}
                onChange={(e) => setBuyer((b) => ({ ...b, phone: e.target.value }))}
                dir="ltr"
                className="text-start"
              />
            </div>
            <div className="space-y-1.5">
              <Label>موبایل</Label>
              <Input
                value={buyer.mobile}
                onChange={(e) => setBuyer((b) => ({ ...b, mobile: e.target.value }))}
                dir="ltr"
                className="text-start"
                placeholder="09…"
              />
            </div>
            <div className="space-y-1.5">
              <Label>کد ملی (اختیاری)</Label>
              <Input
                value={buyer.nationalId}
                onChange={(e) =>
                  setBuyer((b) => ({ ...b, nationalId: e.target.value }))
                }
                dir="ltr"
                className="text-start"
              />
            </div>
            <div className="space-y-1.5 md:col-span-2">
              <Label>آدرس{kind === "invoice" ? " *" : ""}</Label>
              <Textarea
                value={buyer.address}
                onChange={(e) => setBuyer((b) => ({ ...b, address: e.target.value }))}
                rows={2}
                placeholder="آدرس کامل خریدار"
              />
            </div>
            <div className="space-y-1.5">
              <Label>کد پستی{kind === "invoice" ? " *" : ""}</Label>
              <Input
                value={buyer.postalCode ?? ""}
                onChange={(e) =>
                  setBuyer((b) => ({ ...b, postalCode: e.target.value }))
                }
                dir="ltr"
                className="text-start tnum"
                placeholder="۱۰ رقم"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="border-transparent shadow-sm">
        <CardContent className="space-y-4 p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-sm font-bold text-[#4F4F4F]">اقلام</h3>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  setLines((prev) => {
                    const next = [...prev, emptyLine()];
                    setPickerTarget(next.length - 1);
                    setPickerOpen(true);
                    return next;
                  });
                }}
              >
                <Plus set="light" size={16} />
                از کاتالوگ
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setLines((prev) => [...prev, emptyLine()])}
              >
                <Plus set="light" size={16} />
                ردیف دستی
              </Button>
            </div>
          </div>

          <div className="overflow-x-auto rounded-xl border border-[#EFEFEF]">
            <table className="min-w-[920px] w-full text-sm">
              <thead>
                <tr className="bg-[#F7F7F7] text-xs font-bold text-muted-foreground">
                  <th className="px-3 py-2.5 text-start">شرح / SKU</th>
                  <th className="px-2 py-2.5 w-20">تعداد</th>
                  <th className="px-2 py-2.5 w-32">قیمت واحد (تومان)</th>
                  <th className="px-2 py-2.5 w-24">تخفیف %</th>
                  <th className="px-2 py-2.5 w-32">تخفیف مبلغ</th>
                  <th className="px-2 py-2.5 w-28 text-start">خالص</th>
                  <th className="px-2 py-2.5 w-24" />
                </tr>
              </thead>
              <tbody>
                {lines.map((line, index) => {
                  const net = lineNetToman(line);
                  const disc = lineDiscountToman(line);
                  const gross = lineGrossToman(line);
                  return (
                    <tr key={index} className="border-t border-[#EFEFEF] align-top">
                      <td className="space-y-1.5 px-3 py-3">
                        <Input
                          value={line.name}
                          onChange={(e) => updateLine(index, { name: e.target.value })}
                          placeholder="نام کالا"
                        />
                        <div className="flex gap-2">
                          <Input
                            value={line.sku}
                            onChange={(e) => updateLine(index, { sku: e.target.value })}
                            placeholder="SKU"
                            dir="ltr"
                            className="text-start"
                          />
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            className="shrink-0"
                            onClick={() => openPicker(index)}
                          >
                            کاتالوگ
                          </Button>
                        </div>
                      </td>
                      <td className="px-2 py-3">
                        <Input
                          value={String(line.quantity || "")}
                          onChange={(e) =>
                            updateLine(index, { quantity: parseQty(e.target.value) })
                          }
                          dir="ltr"
                          className="text-start tnum"
                        />
                      </td>
                      <td className="px-2 py-3">
                        <Input
                          value={line.unitPriceToman ? String(line.unitPriceToman) : ""}
                          onChange={(e) =>
                            updateLine(index, {
                              unitPriceToman: parseMoney(e.target.value),
                            })
                          }
                          dir="ltr"
                          className="text-start tnum"
                        />
                      </td>
                      <td className="px-2 py-3">
                        <Input
                          value={
                            line.discountPercent ? String(line.discountPercent) : ""
                          }
                          onChange={(e) => {
                            const pct = Math.min(100, parseMoney(e.target.value));
                            // Percent and flat amount are alternatives (not stacked).
                            updateLine(index, {
                              discountPercent: pct,
                              discountAmountToman: pct > 0 ? 0 : line.discountAmountToman,
                            });
                          }}
                          dir="ltr"
                          className="text-start tnum"
                          placeholder="0"
                        />
                      </td>
                      <td className="px-2 py-3">
                        <Input
                          value={
                            line.discountAmountToman
                              ? String(line.discountAmountToman)
                              : ""
                          }
                          onChange={(e) => {
                            const flat = parseMoney(e.target.value);
                            updateLine(index, {
                              discountAmountToman: flat,
                              discountPercent: flat > 0 ? 0 : line.discountPercent,
                            });
                          }}
                          dir="ltr"
                          className="text-start tnum"
                          placeholder="0"
                        />
                        {disc > 0 && (
                          <p className="mt-1 text-[10px] text-muted-foreground tnum">
                            از {formatNumber(gross)} → تخفیف {formatNumber(disc)}
                          </p>
                        )}
                      </td>
                      <td className="px-2 py-3 text-sm font-bold text-[#4F4F4F] tnum">
                        {formatToman(net)}
                      </td>
                      <td className="px-2 py-3">
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          disabled={lines.length <= 1}
                          onClick={() =>
                            setLines((prev) => prev.filter((_, i) => i !== index))
                          }
                          aria-label="حذف ردیف"
                        >
                          <Delete set="light" size={18} primaryColor="#D02327" />
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Card className="border-transparent shadow-sm">
        <CardContent className="space-y-3 p-5">
          <Label>یادداشت داخلی (فقط پنل — روی PDF نمی‌آید)</Label>
          <Textarea
            value={adminNote}
            onChange={(e) => setAdminNote(e.target.value)}
            rows={2}
            placeholder="اختیاری"
          />
        </CardContent>
      </Card>

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-white p-4 shadow-sm">
        <p className="text-sm text-muted-foreground">
          جمع قابل پرداخت:{" "}
          <span className="font-bold text-[#4F4F4F] tnum">{formatToman(grandToman)}</span>
        </p>
        <Button
          type="button"
          size="lg"
          disabled={busy || createIssued.isPending}
          onClick={() => void handleGenerate()}
          className="gap-2"
        >
          <Document set="bold" size={18} primaryColor="#fff" />
          {busy ? "در حال تولید…" : "تولید و دانلود PDF"}
        </Button>
      </div>

      <CatalogProductPicker
        open={pickerOpen}
        onOpenChange={setPickerOpen}
        onPick={(product) => {
          if (pickerTarget == null) return;
          applyProduct(pickerTarget, product);
        }}
      />
    </div>
  );
}
