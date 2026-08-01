"use client";

import { useEffect, useMemo, useState } from "react";
import { ArrowDown, ArrowUp, Category, Delete, Plus } from "react-iconly";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { useFlatCategories } from "@/features/catalog/queries";
import { useNavGroups, useReplaceNavGroups } from "@/features/cms/queries";
import { ApiError } from "@/lib/api-client";
import type { NavGroupReplaceItem } from "@/types/cms";
import type { CategoryFlat } from "@/types/category";
import { cn } from "@/lib/utils";

type DraftGroup = NavGroupReplaceItem & { clientKey: string };

function slugify(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9-_]/g, "")
    .slice(0, 64);
}

function toDraft(groups: NavGroupReplaceItem[]): DraftGroup[] {
  return groups.map((g, idx) => ({
    ...g,
    clientKey: `${g.slug || "group"}-${idx}`,
  }));
}

function findDuplicateRoots(groups: DraftGroup[]): Map<number, string[]> {
  const owners = new Map<number, string[]>();
  for (const group of groups) {
    for (const rootId of group.root_category_ids) {
      const labels = owners.get(rootId) ?? [];
      labels.push(group.label || group.slug || "بدون نام");
      owners.set(rootId, labels);
    }
  }
  const dupes = new Map<number, string[]>();
  for (const [rootId, labels] of owners) {
    if (labels.length > 1) dupes.set(rootId, labels);
  }
  return dupes;
}

export type NavGroupsEditorProps = {
  /** When true, omit the page-level title row (host page supplies chrome). */
  embedded?: boolean;
};

export function NavGroupsEditor({ embedded = false }: NavGroupsEditorProps) {
  const { data, isPending, isError, error, refetch } = useNavGroups();
  const { data: flatCategories = [], isPending: catsPending } = useFlatCategories();
  const replaceMutation = useReplaceNavGroups();

  const l1Roots = useMemo(
    () =>
      (flatCategories as CategoryFlat[])
        .filter((c) => c.parent_id == null || c.depth === 1)
        .sort((a, b) => a.name.localeCompare(b.name, "fa")),
    [flatCategories],
  );

  const rootById = useMemo(() => new Map(l1Roots.map((r) => [r.id, r])), [l1Roots]);

  const [drafts, setDrafts] = useState<DraftGroup[]>([]);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (!data?.data || dirty) return;
    setDrafts(
      toDraft(
        data.data.map((g) => ({
          slug: g.slug,
          label: g.label,
          sort_order: g.sort_order,
          is_enabled: g.is_enabled,
          highlight: g.highlight,
          root_category_ids: [...g.root_category_ids],
        })),
      ),
    );
  }, [data, dirty]);

  const sortedDrafts = useMemo(
    () => [...drafts].sort((a, b) => a.sort_order - b.sort_order || a.slug.localeCompare(b.slug)),
    [drafts],
  );

  const duplicateRoots = useMemo(() => findDuplicateRoots(drafts), [drafts]);

  const assignedElsewhere = useMemo(() => {
    const map = new Map<number, string>();
    for (const group of drafts) {
      for (const rootId of group.root_category_ids) {
        map.set(rootId, group.clientKey);
      }
    }
    return map;
  }, [drafts]);

  function updateDraft(clientKey: string, patch: Partial<NavGroupReplaceItem>) {
    setDirty(true);
    setDrafts((prev) =>
      prev.map((g) => (g.clientKey === clientKey ? { ...g, ...patch } : g)),
    );
  }

  function moveGroup(clientKey: string, direction: -1 | 1) {
    const ordered = [...sortedDrafts];
    const idx = ordered.findIndex((g) => g.clientKey === clientKey);
    const target = idx + direction;
    if (idx < 0 || target < 0 || target >= ordered.length) return;
    const a = ordered[idx];
    const b = ordered[target];
    setDirty(true);
    setDrafts((prev) =>
      prev.map((g) => {
        if (g.clientKey === a.clientKey) return { ...g, sort_order: b.sort_order };
        if (g.clientKey === b.clientKey) return { ...g, sort_order: a.sort_order };
        return g;
      }),
    );
  }

  function addGroup() {
    setDirty(true);
    const nextOrder =
      drafts.length > 0 ? Math.max(...drafts.map((g) => g.sort_order)) + 1 : 0;
    setDrafts((prev) => [
      ...prev,
      {
        clientKey: `new-${Date.now()}`,
        slug: `group-${nextOrder + 1}`,
        label: "گروه جدید",
        sort_order: nextOrder,
        is_enabled: true,
        highlight: false,
        root_category_ids: [],
      },
    ]);
  }

  function removeGroup(clientKey: string) {
    if (drafts.length <= 1) {
      toast.error("حداقل یک گروه باید باقی بماند");
      return;
    }
    setDirty(true);
    setDrafts((prev) => prev.filter((g) => g.clientKey !== clientKey));
  }

  function toggleRoot(clientKey: string, rootId: number) {
    const group = drafts.find((g) => g.clientKey === clientKey);
    if (!group) return;
    const owner = assignedElsewhere.get(rootId);
    if (owner && owner !== clientKey) {
      const ownerLabel = drafts.find((g) => g.clientKey === owner)?.label ?? "گروه دیگر";
      toast.error(`این ریشه قبلاً در «${ownerLabel}» است`);
      return;
    }
    const ids = group.root_category_ids.includes(rootId)
      ? group.root_category_ids.filter((id) => id !== rootId)
      : [...group.root_category_ids, rootId];
    updateDraft(clientKey, { root_category_ids: ids });
  }

  function moveRoot(clientKey: string, rootId: number, direction: -1 | 1) {
    const group = drafts.find((g) => g.clientKey === clientKey);
    if (!group) return;
    const ids = [...group.root_category_ids];
    const idx = ids.indexOf(rootId);
    const target = idx + direction;
    if (idx < 0 || target < 0 || target >= ids.length) return;
    [ids[idx], ids[target]] = [ids[target], ids[idx]];
    updateDraft(clientKey, { root_category_ids: ids });
  }

  async function handleSave() {
    if (duplicateRoots.size > 0) {
      toast.error("یک ریشه نمی‌تواند در دو گروه باشد");
      return;
    }
    const slugs = drafts.map((g) => g.slug.trim());
    if (new Set(slugs).size !== slugs.length) {
      toast.error("شناسه (slug) گروه‌ها نباید تکراری باشد");
      return;
    }
    for (const g of drafts) {
      if (!g.label.trim()) {
        toast.error("برچسب همه گروه‌ها الزامی است");
        return;
      }
      if (!g.slug.trim() || !/^[a-z0-9][a-z0-9-_]*$/i.test(g.slug.trim())) {
        toast.error(`شناسه نامعتبر: ${g.slug || "خالی"}`);
        return;
      }
    }

    try {
      await replaceMutation.mutateAsync({
        groups: drafts.map((g) => ({
          slug: g.slug.trim(),
          label: g.label.trim(),
          sort_order: g.sort_order,
          is_enabled: g.is_enabled,
          highlight: g.highlight,
          root_category_ids: g.root_category_ids,
        })),
      });
      setDirty(false);
      toast.success("گروه‌های مگامنو ذخیره شد");
    } catch (err) {
      const message =
        err instanceof ApiError
          ? Object.values(err.fieldErrors)[0] || err.message
          : "ذخیره ناموفق بود";
      toast.error(message);
    }
  }

  function handleReset() {
    if (!data?.data) return;
    setDrafts(
      toDraft(
        data.data.map((g) => ({
          slug: g.slug,
          label: g.label,
          sort_order: g.sort_order,
          is_enabled: g.is_enabled,
          highlight: g.highlight,
          root_category_ids: [...g.root_category_ids],
        })),
      ),
    );
    setDirty(false);
  }

  const actions = (
    <div className="flex flex-wrap items-center gap-2">
      <Button variant="outline" onClick={addGroup}>
        <Plus set="bold" size={18} />
        افزودن گروه
      </Button>
      <Button variant="outline" disabled={!dirty} onClick={handleReset}>
        بازنشانی
      </Button>
      <Button
        onClick={() => void handleSave()}
        disabled={!dirty || replaceMutation.isPending || duplicateRoots.size > 0}
      >
        {replaceMutation.isPending ? "در حال ذخیره…" : "ذخیره تغییرات"}
      </Button>
    </div>
  );

  return (
    <div className={cn("flex flex-col gap-6", !embedded && "mx-auto max-w-7xl")}>
      {embedded ? (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="max-w-2xl text-sm text-muted-foreground">
            گروه‌های نمایشی مگامنو فروشگاه — هر گروه شامل ریشه‌های لایه ۱ است. گروه‌های خالی یا بدون
            محصول در فروشگاه مخفی می‌شوند.
          </p>
          {actions}
        </div>
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold text-[#4F4F4F]">گروه‌های مگامنو</h2>
            <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
              گروه‌های نمایشی منوی فروشگاه را مدیریت کنید. هر گروه شامل یک یا چند ریشه لایه ۱ است.
              گروه‌های خالی یا بدون محصول در فروشگاه مخفی می‌شوند.
            </p>
          </div>
          {actions}
        </div>
      )}

      {duplicateRoots.size > 0 && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          ریشه تکراری بین گروه‌ها وجود دارد. قبل از ذخیره، هر ریشه فقط در یک گروه باشد.
        </div>
      )}

      {isPending || catsPending ? (
        <div className="flex flex-col gap-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-40 w-full" />
          ))}
        </div>
      ) : isError ? (
        <Card className="border-transparent shadow-sm">
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
            <p className="text-sm font-bold">
              {error instanceof ApiError ? error.message : "خطا در دریافت گروه‌ها"}
            </p>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              تلاش مجدد
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
          <div className="flex flex-col gap-4">
            {sortedDrafts.map((group, index) => (
              <Card key={group.clientKey} className="border-transparent shadow-sm">
                <CardContent className="flex flex-col gap-4 p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <Badge variant="neutral">#{index + 1}</Badge>
                      {group.highlight && <Badge>برجسته</Badge>}
                      {!group.is_enabled && <Badge variant="outline">غیرفعال</Badge>}
                    </div>
                    <div className="flex items-center gap-1">
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        aria-label="بالا"
                        onClick={() => moveGroup(group.clientKey, -1)}
                        disabled={index === 0}
                      >
                        <ArrowUp set="bold" size={18} />
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        aria-label="پایین"
                        onClick={() => moveGroup(group.clientKey, 1)}
                        disabled={index === sortedDrafts.length - 1}
                      >
                        <ArrowDown set="bold" size={18} />
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        aria-label="حذف گروه"
                        onClick={() => removeGroup(group.clientKey)}
                      >
                        <Delete set="bold" size={18} primaryColor="#D02327" />
                      </Button>
                    </div>
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="space-y-1.5">
                      <Label htmlFor={`label-${group.clientKey}`}>برچسب فارسی</Label>
                      <Input
                        id={`label-${group.clientKey}`}
                        value={group.label}
                        onChange={(e) => updateDraft(group.clientKey, { label: e.target.value })}
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor={`slug-${group.clientKey}`}>شناسه (انگلیسی)</Label>
                      <Input
                        id={`slug-${group.clientKey}`}
                        value={group.slug}
                        dir="ltr"
                        className="font-mono text-sm"
                        onChange={(e) =>
                          updateDraft(group.clientKey, {
                            slug: slugify(e.target.value) || e.target.value,
                          })
                        }
                      />
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-6">
                    <div className="flex items-center gap-2">
                      <Switch
                        checked={group.is_enabled}
                        onCheckedChange={(checked) =>
                          updateDraft(group.clientKey, { is_enabled: checked })
                        }
                        aria-label="فعال بودن گروه"
                      />
                      <span className="text-sm">فعال در فروشگاه</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Switch
                        checked={group.highlight}
                        onCheckedChange={(checked) =>
                          updateDraft(group.clientKey, { highlight: checked })
                        }
                        aria-label="برجسته بودن گروه"
                      />
                      <span className="text-sm">برجسته (مثل اندازه‌گیری)</span>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>ریشه‌های لایه ۱ (به ترتیب نمایش)</Label>
                    {group.root_category_ids.length === 0 ? (
                      <p className="text-xs text-muted-foreground">
                        هنوز ریشه‌ای انتخاب نشده — گروه در مگامنو مخفی می‌ماند.
                      </p>
                    ) : (
                      <ul className="flex flex-col gap-1">
                        {group.root_category_ids.map((rootId, rootIdx) => {
                          const root = rootById.get(rootId);
                          return (
                            <li
                              key={rootId}
                              className="flex items-center justify-between gap-2 rounded-lg bg-muted/40 px-3 py-2 text-sm"
                            >
                              <span>{root?.name ?? `شناسه ${rootId}`}</span>
                              <div className="flex items-center gap-1">
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="icon"
                                  className="h-8 w-8"
                                  aria-label="بالا بردن ریشه"
                                  disabled={rootIdx === 0}
                                  onClick={() => moveRoot(group.clientKey, rootId, -1)}
                                >
                                  <ArrowUp set="bold" size={14} />
                                </Button>
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="icon"
                                  className="h-8 w-8"
                                  aria-label="پایین بردن ریشه"
                                  disabled={rootIdx === group.root_category_ids.length - 1}
                                  onClick={() => moveRoot(group.clientKey, rootId, 1)}
                                >
                                  <ArrowDown set="bold" size={14} />
                                </Button>
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => toggleRoot(group.clientKey, rootId)}
                                >
                                  حذف
                                </Button>
                              </div>
                            </li>
                          );
                        })}
                      </ul>
                    )}

                    <div className="mt-2 flex flex-wrap gap-2">
                      {l1Roots.map((root) => {
                        const selected = group.root_category_ids.includes(root.id);
                        const ownedByOther =
                          assignedElsewhere.has(root.id) &&
                          assignedElsewhere.get(root.id) !== group.clientKey;
                        return (
                          <button
                            key={root.id}
                            type="button"
                            disabled={ownedByOther}
                            onClick={() => toggleRoot(group.clientKey, root.id)}
                            className={cn(
                              "rounded-full border px-3 py-1.5 text-xs transition-colors",
                              selected
                                ? "border-primary bg-primary/10 text-primary"
                                : ownedByOther
                                  ? "cursor-not-allowed border-border/40 text-muted-foreground/50"
                                  : "border-border text-foreground hover:border-primary/40",
                            )}
                            title={
                              ownedByOther
                                ? "در گروه دیگری استفاده شده"
                                : selected
                                  ? "حذف از این گروه"
                                  : "افزودن به این گروه"
                            }
                          >
                            {root.name}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          <Card className="h-fit border-transparent shadow-sm lg:sticky lg:top-4">
            <CardContent className="flex flex-col gap-4 p-5">
              <div className="flex items-center gap-2">
                <Category set="bold" size={22} primaryColor="#D02327" />
                <h3 className="text-base font-bold text-[#4F4F4F]">پیش‌نمایش مگامنو</h3>
              </div>
              <p className="text-xs text-muted-foreground">
                ترتیب و اعضای فعال (با محصول در فروشگاه فیلتر می‌شوند).
              </p>
              <ol className="flex flex-col gap-3">
                {sortedDrafts
                  .filter((g) => g.is_enabled)
                  .map((group) => (
                    <li key={group.clientKey} className="rounded-xl bg-muted/30 p-3">
                      <div className="mb-2 flex items-center gap-2">
                        <span className="text-sm font-bold">{group.label}</span>
                        {group.highlight && (
                          <Badge className="text-[10px]">برجسته</Badge>
                        )}
                      </div>
                      {group.root_category_ids.length === 0 ? (
                        <p className="text-xs text-muted-foreground">بدون ریشه — مخفی در فروشگاه</p>
                      ) : (
                        <ul className="flex flex-col gap-1 text-xs text-muted-foreground">
                          {group.root_category_ids.map((id) => (
                            <li key={id}>• {rootById.get(id)?.name ?? `شناسه ${id}`}</li>
                          ))}
                        </ul>
                      )}
                    </li>
                  ))}
              </ol>
              {l1Roots.some((r) => !assignedElsewhere.has(r.id)) && (
                <div className="rounded-xl border border-dashed border-border p-3">
                  <p className="mb-2 text-xs font-bold text-foreground">ریشه‌های بدون گروه</p>
                  <ul className="flex flex-col gap-1 text-xs text-muted-foreground">
                    {l1Roots
                      .filter((r) => !assignedElsewhere.has(r.id))
                      .map((r) => (
                        <li key={r.id}>• {r.name}</li>
                      ))}
                  </ul>
                  <p className="mt-2 text-[11px] text-muted-foreground">
                    این ریشه‌ها در فروشگاه به‌صورت گروه تکی اضافه می‌شوند.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
