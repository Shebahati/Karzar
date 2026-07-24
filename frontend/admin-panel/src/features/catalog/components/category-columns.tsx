"use client";

import { Delete, Edit, Plus } from "react-iconly";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { CategoryFlat } from "@/types/category";

interface CategoryColumnProps {
  title: string;
  items: CategoryFlat[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  onAdd?: () => void;
  onEdit?: (category: CategoryFlat) => void;
  onDelete?: (category: CategoryFlat) => void;
  emptyHint?: string;
}

function CategoryColumn({
  title,
  items,
  selectedId,
  onSelect,
  onAdd,
  onEdit,
  onDelete,
  emptyHint,
}: CategoryColumnProps) {
  return (
    <div className="flex min-h-[420px] flex-col rounded-xl bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
        <h3 className="text-sm font-bold text-[#4F4F4F]">{title}</h3>
        {onAdd && (
          <Button type="button" variant="ghost" size="icon" aria-label="افزودن" onClick={onAdd}>
            <Plus set="bold" size={18} primaryColor="#C22026" />
          </Button>
        )}
      </div>
      <ul className="flex-1 overflow-y-auto p-2">
        {items.length === 0 ? (
          <li className="px-3 py-8 text-center text-xs text-muted-foreground">{emptyHint}</li>
        ) : (
          items.map((item) => {
            const active = item.id === selectedId;
            return (
              <li key={item.id} className="mb-1">
                <div
                  className={cn(
                    "group flex items-center gap-1 rounded-lg px-3 py-2.5 transition-colors",
                    active ? "bg-accent text-primary" : "hover:bg-[#F7F7F7]",
                  )}
                >
                  <button
                    type="button"
                    className="min-w-0 flex-1 truncate text-start text-sm font-bold"
                    onClick={() => onSelect(item.id)}
                  >
                    <span className="block truncate">{item.name}</span>
                    <span className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[10px] font-medium text-muted-foreground">
                      <span>عمق {item.depth}</span>
                      {item.is_selectable ? (
                        <span className="rounded bg-emerald-50 px-1 text-emerald-700">قابل انتخاب</span>
                      ) : (
                        <span className="rounded bg-gray-100 px-1">غیرقابل‌انتخاب</span>
                      )}
                      <span>
                        {(item.product_count ?? 0).toLocaleString("fa-IR")} محصول
                      </span>
                      {(item.product_count ?? 0) === 0 ? (
                        <span className="rounded bg-amber-50 px-1 text-amber-800">
                          {item.is_leaf ? "خالی" : "بدون محصول (مرده)"}
                        </span>
                      ) : null}
                      {item.name.trim().startsWith("استاندارد") ||
                      /(?:—|-|–)\s*عمومی\s*$/.test(item.name.trim()) ? (
                        <span className="rounded bg-orange-50 px-1 text-orange-700">
                          {item.name.trim().startsWith("استاندارد") ? "استاندارد" : "عمومی/پدینگ"}
                        </span>
                      ) : null}
                    </span>
                  </button>
                  <div className="flex shrink-0 opacity-0 transition-opacity group-hover:opacity-100">
                    {onEdit && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => onEdit(item)}
                      >
                        <Edit set="light" size={16} primaryColor="currentColor" />
                      </Button>
                    )}
                    {onDelete && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-destructive hover:bg-destructive/10"
                        onClick={() => onDelete(item)}
                      >
                        <Delete set="light" size={16} primaryColor="currentColor" />
                      </Button>
                    )}
                  </div>
                </div>
              </li>
            );
          })
        )}
      </ul>
    </div>
  );
}

interface CategoryColumnsProps {
  categories: CategoryFlat[];
  layer1Id: number | null;
  layer2Id: number | null;
  onSelectLayer1: (id: number) => void;
  onSelectLayer2: (id: number) => void;
  onAddLayer1: () => void;
  onAddLayer2: () => void;
  onAddLayer3: () => void;
  onEdit: (category: CategoryFlat) => void;
  onDelete: (category: CategoryFlat) => void;
}

export function CategoryColumns({
  categories,
  layer1Id,
  layer2Id,
  onSelectLayer1,
  onSelectLayer2,
  onAddLayer1,
  onAddLayer2,
  onAddLayer3,
  onEdit,
  onDelete,
}: CategoryColumnsProps) {
  const layer1 = categories.filter((c) => c.depth === 1);
  const layer2 = layer1Id
    ? categories.filter((c) => c.depth === 2 && c.parent_id === layer1Id)
    : [];
  const layer3 = layer2Id
    ? categories.filter((c) => c.depth === 3 && c.parent_id === layer2Id)
    : [];

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
      <CategoryColumn
        title="لایه ۱ — دسته اصلی"
        items={layer1}
        selectedId={layer1Id}
        onSelect={onSelectLayer1}
        onAdd={onAddLayer1}
        onEdit={onEdit}
        onDelete={onDelete}
        emptyHint="دسته اصلی وجود ندارد"
      />
      <CategoryColumn
        title="لایه ۲ — زیردسته"
        items={layer2}
        selectedId={layer2Id}
        onSelect={onSelectLayer2}
        onAdd={layer1Id ? onAddLayer2 : undefined}
        onEdit={onEdit}
        onDelete={onDelete}
        emptyHint={layer1Id ? "زیردسته‌ای نیست" : "ابتدا لایه ۱ را انتخاب کنید"}
      />
      <CategoryColumn
        title="لایه ۳ — دسته محصول"
        items={layer3}
        selectedId={null}
        onSelect={() => undefined}
        onAdd={layer2Id ? onAddLayer3 : undefined}
        onEdit={onEdit}
        onDelete={onDelete}
        emptyHint={layer2Id ? "دسته محصولی نیست" : "ابتدا لایه ۲ را انتخاب کنید"}
      />
    </div>
  );
}
