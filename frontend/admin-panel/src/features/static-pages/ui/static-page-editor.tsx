"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowDown, ArrowUp, Delete, Plus } from "react-iconly";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { createEmptySection } from "@/features/static-pages/defaults";
import { cn } from "@/lib/utils";
import { staticPagesService } from "@/services/static-pages";
import {
  STATIC_PAGE_META,
  type StaticContactFields,
  type StaticPageDocument,
  type StaticPageSection,
  type StaticPageSlug,
} from "@/types/static-pages";

const SLUGS = Object.keys(STATIC_PAGE_META) as StaticPageSlug[];

function isValidSlug(value: string): value is StaticPageSlug {
  return SLUGS.includes(value as StaticPageSlug);
}

function linesToList(text: string): string[] {
  return text
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);
}

function listToLines(items: string[] | undefined): string {
  return (items ?? []).join("\n");
}

function relatedToLines(
  related: StaticPageSection["related"] | undefined,
): string {
  return (related ?? []).map((r) => `${r.label}|${r.href}`).join("\n");
}

function linesToRelated(text: string): StaticPageSection["related"] {
  const rows = linesToList(text)
    .map((line) => {
      const sep = line.indexOf("|");
      if (sep < 0) return null;
      const label = line.slice(0, sep).trim();
      const href = line.slice(sep + 1).trim();
      if (!label || !href) return null;
      return { label, href };
    })
    .filter((r): r is { label: string; href: string } => Boolean(r));
  return rows.length ? rows : undefined;
}

type Props = { slug: string };

export function StaticPageEditor({ slug: rawSlug }: Props) {
  const slug = isValidSlug(rawSlug) ? rawSlug : null;
  const [doc, setDoc] = useState<StaticPageDocument | null>(null);
  const [dirty, setDirty] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    if (!slug) return;
    setDoc(staticPagesService.get(slug));
    setDirty(false);
    setExpandedId(null);
  }, [slug]);

  if (!slug) {
    return (
      <div className="mx-auto max-w-3xl rounded-2xl border border-border/60 bg-card p-8 text-center shadow-sm">
        <p className="font-bold text-foreground">صفحه یافت نشد</p>
        <p className="mt-2 text-sm text-muted-foreground">
          فقط contact / about / terms / privacy پشتیبانی می‌شوند.
        </p>
        <Button asChild variant="outline" size="sm" className="mt-4">
          <Link href="/cms/static-pages">بازگشت به فهرست</Link>
        </Button>
      </div>
    );
  }

  const pageSlug: StaticPageSlug = slug;

  if (!doc) {
    return (
      <div className="mx-auto flex max-w-3xl flex-col gap-4">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  const meta = STATIC_PAGE_META[pageSlug];

  function patchDoc(updater: (prev: StaticPageDocument) => StaticPageDocument) {
    setDoc((prev) => (prev ? updater(prev) : prev));
    setDirty(true);
  }

  function updateSections(
    updater: (prev: StaticPageSection[]) => StaticPageSection[],
  ) {
    patchDoc((prev) => ({ ...prev, sections: updater(prev.sections) }));
  }

  function moveSection(id: string, direction: -1 | 1) {
    updateSections((prev) => {
      const idx = prev.findIndex((s) => s.id === id);
      const next = idx + direction;
      if (idx < 0 || next < 0 || next >= prev.length) return prev;
      const copy = [...prev];
      const [item] = copy.splice(idx, 1);
      copy.splice(next, 0, item);
      return copy;
    });
  }

  function patchSection(id: string, patch: Partial<StaticPageSection>) {
    updateSections((prev) =>
      prev.map((s) => (s.id === id ? { ...s, ...patch } : s)),
    );
  }

  function addSection() {
    const section = createEmptySection();
    updateSections((prev) => [...prev, section]);
    setExpandedId(section.id);
  }

  function removeSection(id: string) {
    updateSections((prev) => prev.filter((s) => s.id !== id));
    if (expandedId === id) setExpandedId(null);
  }

  function patchContact(patch: Partial<StaticContactFields>) {
    patchDoc((prev) => ({
      ...prev,
      contact: { ...(prev.contact as StaticContactFields), ...patch },
    }));
  }

  function handleSave() {
    if (!doc) return;
    const saved = staticPagesService.save(doc);
    setDoc(saved);
    setDirty(false);
    toast.success("پیش‌نویس در این مرورگر ذخیره شد");
  }

  function handleReset() {
    if (
      !window.confirm(
        "محتوای این صفحه به نسخهٔ پیش‌فرض فروشگاه برگردد؟ تغییرات ذخیره‌نشده از بین می‌رود.",
      )
    ) {
      return;
    }
    const next = staticPagesService.reset(pageSlug);
    setDoc(next);
    setDirty(false);
    setExpandedId(null);
    toast.success("به پیش‌فرض بازگردانده شد");
  }

  async function handleExport() {
    try {
      const json = staticPagesService.exportJson(pageSlug);
      await navigator.clipboard.writeText(json);
      toast.success("JSON در کلیپ‌بورد کپی شد");
    } catch {
      toast.error("کپی JSON ناموفق بود");
    }
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link
            href="/cms/static-pages"
            className="text-xs font-bold text-muted-foreground transition-colors hover:text-primary"
          >
            ← مدیریت محتوای صفحات
          </Link>
          <h2 className="mt-2 text-2xl font-bold text-[#4F4F4F]">{meta.label}</h2>
          <p className="mt-1 text-sm text-muted-foreground">{meta.description}</p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <Badge variant="outline" className="text-[10px]" dir="ltr">
              {meta.hrefPreview}
            </Badge>
            <Badge
              variant="outline"
              className="border-amber-300 bg-amber-50 text-[10px] text-amber-800"
            >
              پیش‌نویس محلی — فروشگاه متصل نیست
            </Badge>
            {dirty ? (
              <span className="text-xs text-amber-700">تغییرات ذخیره نشده</span>
            ) : null}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" size="sm" onClick={handleExport}>
            کپی JSON
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={handleReset}>
            بازنشانی پیش‌فرض
          </Button>
          <Button
            type="button"
            size="sm"
            className="bg-[#D02327] hover:bg-[#B01E22]"
            onClick={handleSave}
          >
            ذخیره پیش‌نویس
          </Button>
        </div>
      </div>

      <div className="rounded-2xl border border-amber-200/80 bg-amber-50/80 px-4 py-3 text-sm leading-7 text-amber-950">
        ذخیره فقط در localStorage همین مرورگر است. صفحهٔ زنده فروشگاه تا اتصال
        backend یا انتشار رسمی تغییر نمی‌کند.
      </div>

      <Card className="border-transparent shadow-sm">
        <CardContent className="grid gap-4 p-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="page-eyebrow">برچسب / Eyebrow</Label>
              <Input
                id="page-eyebrow"
                value={doc.eyebrow}
                onChange={(e) =>
                  patchDoc((prev) => ({ ...prev, eyebrow: e.target.value }))
                }
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="page-updated">برچسب به‌روزرسانی</Label>
              <Input
                id="page-updated"
                value={doc.updatedLabel ?? ""}
                onChange={(e) =>
                  patchDoc((prev) => ({
                    ...prev,
                    updatedLabel: e.target.value,
                  }))
                }
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="page-title">عنوان صفحه</Label>
            <Input
              id="page-title"
              value={doc.title}
              onChange={(e) =>
                patchDoc((prev) => ({ ...prev, title: e.target.value }))
              }
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="page-intro">مقدمه</Label>
            <Textarea
              id="page-intro"
              rows={4}
              value={doc.intro}
              onChange={(e) =>
                patchDoc((prev) => ({ ...prev, intro: e.target.value }))
              }
            />
          </div>
        </CardContent>
      </Card>

      {pageSlug === "contact" && doc.contact ? (
        <Card className="border-transparent shadow-sm">
          <CardContent className="grid gap-4 p-5">
            <div>
              <h3 className="text-sm font-bold text-[#4F4F4F]">اطلاعات تماس</h3>
              <p className="mt-0.5 text-xs text-muted-foreground">
                در فروشگاه فعلی از فایل store-location خوانده می‌شود؛ اینجا فقط پیش‌نویس است.
              </p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label>تلفن نمایشی</Label>
                <Input
                  dir="ltr"
                  value={doc.contact.phoneDisplay}
                  onChange={(e) =>
                    patchContact({ phoneDisplay: e.target.value })
                  }
                />
              </div>
              <div className="space-y-1.5">
                <Label>تلفن E.164</Label>
                <Input
                  dir="ltr"
                  value={doc.contact.phoneE164}
                  onChange={(e) => patchContact({ phoneE164: e.target.value })}
                />
              </div>
              <div className="space-y-1.5 sm:col-span-2">
                <Label>ایمیل</Label>
                <Input
                  dir="ltr"
                  value={doc.contact.email}
                  onChange={(e) => patchContact({ email: e.target.value })}
                />
              </div>
              <div className="space-y-1.5 sm:col-span-2">
                <Label>نشانی</Label>
                <Textarea
                  rows={3}
                  value={doc.contact.address}
                  onChange={(e) => patchContact({ address: e.target.value })}
                />
              </div>
              <div className="space-y-1.5 sm:col-span-2">
                <Label>کپشن نقشه</Label>
                <Input
                  value={doc.contact.addressMapCaption}
                  onChange={(e) =>
                    patchContact({ addressMapCaption: e.target.value })
                  }
                />
              </div>
              <div className="space-y-1.5">
                <Label>تلگرام</Label>
                <Input
                  dir="ltr"
                  value={doc.contact.telegramUrl}
                  onChange={(e) =>
                    patchContact({ telegramUrl: e.target.value })
                  }
                />
              </div>
              <div className="space-y-1.5">
                <Label>واتساپ</Label>
                <Input
                  dir="ltr"
                  value={doc.contact.whatsappUrl}
                  onChange={(e) =>
                    patchContact({ whatsappUrl: e.target.value })
                  }
                />
              </div>
              <div className="space-y-1.5 sm:col-span-2">
                <Label>اینستاگرام</Label>
                <Input
                  dir="ltr"
                  value={doc.contact.instagramUrl}
                  onChange={(e) =>
                    patchContact({ instagramUrl: e.target.value })
                  }
                />
              </div>
            </div>
          </CardContent>
        </Card>
      ) : null}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-base font-bold text-[#4F4F4F]">بخش‌ها</h3>
        <Button type="button" variant="outline" size="sm" onClick={addSection}>
          <Plus set="light" size={16} />
          افزودن بخش
        </Button>
      </div>

      <Card className="border-transparent shadow-sm">
        <CardContent className="divide-y divide-gray-100 p-0">
          {doc.sections.length === 0 ? (
            <p className="px-4 py-8 text-center text-sm text-muted-foreground">
              هنوز بخشی نیست — «افزودن بخش» را بزنید.
            </p>
          ) : null}
          {doc.sections.map((section, index) => {
            const expanded = expandedId === section.id;
            return (
              <div
                key={section.id}
                className={cn("px-4 py-4 transition-colors")}
              >
                <div className="flex flex-wrap items-center gap-3">
                  <span className="w-6 text-center text-xs tabular-nums text-muted-foreground">
                    {index + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <span className="text-sm font-bold text-[#4F4F4F]">
                      {section.title.trim() || "بدون عنوان"}
                    </span>
                    <p className="mt-0.5 line-clamp-1 text-xs text-muted-foreground">
                      {section.paragraphs[0] || "بدون متن"}
                    </p>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      disabled={index === 0}
                      aria-label="جابجایی به بالا"
                      onClick={() => moveSection(section.id, -1)}
                    >
                      <ArrowUp set="light" size={16} />
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      disabled={index === doc.sections.length - 1}
                      aria-label="جابجایی به پایین"
                      onClick={() => moveSection(section.id, 1)}
                    >
                      <ArrowDown set="light" size={16} />
                    </Button>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      setExpandedId(expanded ? null : section.id)
                    }
                  >
                    {expanded ? "بستن" : "ویرایش"}
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-destructive"
                    aria-label="حذف بخش"
                    onClick={() => removeSection(section.id)}
                  >
                    <Delete set="light" size={16} />
                  </Button>
                </div>

                {expanded ? (
                  <div className="mt-4 grid gap-3 rounded-lg border border-border/60 bg-white p-4">
                    <div className="space-y-1.5">
                      <Label>عنوان بخش</Label>
                      <Input
                        value={section.title}
                        onChange={(e) =>
                          patchSection(section.id, { title: e.target.value })
                        }
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label>متن‌ها (هر پاراگراف در یک خط جدا)</Label>
                      <Textarea
                        rows={5}
                        value={listToLines(section.paragraphs)}
                        onChange={(e) =>
                          patchSection(section.id, {
                            paragraphs: linesToList(e.target.value).length
                              ? linesToList(e.target.value)
                              : [""],
                          })
                        }
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label>بولت‌ها (اختیاری — هر مورد یک خط)</Label>
                      <Textarea
                        rows={4}
                        value={listToLines(section.bullets)}
                        onChange={(e) => {
                          const bullets = linesToList(e.target.value);
                          patchSection(section.id, {
                            bullets: bullets.length ? bullets : undefined,
                          });
                        }}
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label>یادداشت / callout (اختیاری)</Label>
                      <Textarea
                        rows={2}
                        value={section.note ?? ""}
                        onChange={(e) =>
                          patchSection(section.id, {
                            note: e.target.value || undefined,
                          })
                        }
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label>
                        لینک‌های مرتبط (اختیاری — قالب:{" "}
                        <span dir="ltr" className="font-mono text-[11px]">
                          برچسب|/path
                        </span>
                        )
                      </Label>
                      <Textarea
                        rows={2}
                        dir="ltr"
                        className="text-left"
                        value={relatedToLines(section.related)}
                        onChange={(e) =>
                          patchSection(section.id, {
                            related: linesToRelated(e.target.value),
                          })
                        }
                      />
                    </div>
                  </div>
                ) : null}
              </div>
            );
          })}
        </CardContent>
      </Card>
    </div>
  );
}
