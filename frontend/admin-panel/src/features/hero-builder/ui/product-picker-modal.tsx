"use client";

import { useMemo, useState } from "react";
import { useProducts } from "@/features/catalog/queries";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export function ProductPickerModal({
  open,
  onOpenChange,
  selectedIds,
  onConfirm,
  maxItems = 8,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  selectedIds: number[];
  onConfirm: (ids: number[], titles: string[]) => void;
  maxItems?: number;
}) {
  const [q, setQ] = useState("");
  const [draft, setDraft] = useState<number[]>(selectedIds);
  const { data, isPending } = useProducts({ limit: 60, search: q || undefined });
  const rows = data?.data ?? [];

  const selectedTitles = useMemo(() => {
    const map = new Map(rows.map((p) => [p.id, p.name]));
    return draft.map((id) => map.get(id) ?? `محصول #${id}`);
  }, [draft, rows]);

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        if (v) setDraft(selectedIds);
        onOpenChange(v);
      }}
    >
      <DialogContent className="max-h-[85vh] max-w-xl overflow-hidden">
        <DialogHeader>
          <DialogTitle>انتخاب محصولات کروسل</DialogTitle>
          <DialogDescription>
            حداکثر {maxItems} محصول — ترتیب انتخاب = ترتیب نمایش
          </DialogDescription>
        </DialogHeader>

        <Input
          placeholder="جستجوی نام یا SKU…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />

        <div className="max-h-[42vh] space-y-1 overflow-y-auto rounded-xl bg-muted/40 p-2">
          {isPending ? (
            <p className="p-3 text-sm text-muted-foreground">در حال بارگذاری…</p>
          ) : rows.length === 0 ? (
            <p className="p-3 text-sm text-muted-foreground">محصولی یافت نشد</p>
          ) : (
            rows.map((p) => {
              const checked = draft.includes(p.id);
              const disabled = !checked && draft.length >= maxItems;
              return (
                <button
                  key={p.id}
                  type="button"
                  disabled={disabled}
                  onClick={() =>
                    setDraft((ids) =>
                      checked ? ids.filter((x) => x !== p.id) : [...ids, p.id],
                    )
                  }
                  className={cn(
                    "flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-start text-sm transition",
                    checked ? "bg-primary/10 text-ink" : "hover:bg-card",
                    disabled && "opacity-40",
                  )}
                >
                  <span
                    className={cn(
                      "grid h-5 w-5 place-items-center rounded-md text-[10px] font-black",
                      checked ? "bg-primary text-white" : "bg-card text-muted-foreground",
                    )}
                  >
                    {checked ? "✓" : "+"}
                  </span>
                  <span className="min-w-0 flex-1 truncate font-bold">{p.name}</span>
                  <span className="shrink-0 text-[10px] text-muted-foreground" dir="ltr">
                    #{p.id}
                  </span>
                </button>
              );
            })
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-2">
          <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
            انصراف
          </Button>
          <Button
            type="button"
            onClick={() => {
              onConfirm(draft, selectedTitles);
              onOpenChange(false);
            }}
          >
            تأیید ({draft.length})
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
