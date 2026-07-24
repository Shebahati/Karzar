"use client";

import { useMemo, useState } from "react";
import { Category, ChevronDown, TickSquare } from "react-iconly";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  formatCategoryLabel,
  getSelectableCategories,
} from "@/features/catalog/utils/specifications";
import type { CategoryFlat } from "@/types/category";

interface CategoryLeafComboboxProps {
  categories: CategoryFlat[];
  value: string;
  onChange: (categoryId: string) => void;
  loading?: boolean;
  disabled?: boolean;
  error?: boolean;
}

/**
 * Command/Combobox restricted to layer-3 leaf categories (depth 3, no children).
 */
export function CategoryLeafCombobox({
  categories,
  value,
  onChange,
  loading,
  disabled,
  error,
}: CategoryLeafComboboxProps) {
  const [open, setOpen] = useState(false);

  const selectable = useMemo(() => getSelectableCategories(categories), [categories]);
  const selected = selectable.find((c) => String(c.id) === value);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          disabled={disabled || loading}
          aria-invalid={error}
          className={cn(
            "h-11 w-full justify-between bg-input font-normal shadow-soft hover:bg-card",
            !selected && "text-muted-foreground",
          )}
        >
          <span className="flex min-w-0 items-center gap-2">
            <Category set="light" size={18} primaryColor="#828282" />
            <span className="truncate text-start">
              {loading
                ? "در حال بارگذاری دسته‌بندی‌ها..."
                : selected
                  ? formatCategoryLabel(selected)
                  : "انتخاب دسته‌بندی لایه ۳"}
            </span>
          </span>
          <ChevronDown set="light" size={18} primaryColor="#828282" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="p-0">
        <Command>
          <CommandInput placeholder="جستجوی دسته‌بندی..." />
          <CommandList>
            <CommandEmpty>دسته‌بندی لایه ۳ یافت نشد.</CommandEmpty>
            <CommandGroup>
              {selectable.map((category) => {
                const label = formatCategoryLabel(category);
                const isSelected = String(category.id) === value;
                return (
                  <CommandItem
                    key={category.id}
                    value={label}
                    onSelect={() => {
                      onChange(String(category.id));
                      setOpen(false);
                    }}
                  >
                    <div className="flex min-w-0 flex-1 flex-col gap-0.5 text-start">
                      <span className="truncate text-sm font-bold">{category.name}</span>
                      <span className="truncate text-xs text-muted-foreground">
                        {category.breadcrumb.slice(0, -1).join(" / ")}
                      </span>
                    </div>
                    {isSelected && (
                      <TickSquare set="bold" size={16} primaryColor="#C22026" />
                    )}
                  </CommandItem>
                );
              })}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
