"use client";

import { useState } from "react";
import { Bag2, ChevronDown, TickSquare } from "react-iconly";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
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
import { useProducts } from "@/features/catalog/queries";

interface RelatedProductsPickerProps {
  value: number[];
  onChange: (ids: number[]) => void;
  disabled?: boolean;
}

/** Multi-select combobox for linking an article to catalog products. */
export function RelatedProductsPicker({ value, onChange, disabled }: RelatedProductsPickerProps) {
  const [open, setOpen] = useState(false);
  const { data, isPending } = useProducts({ limit: 100 });
  const products = data?.data ?? [];

  function toggle(id: number) {
    onChange(value.includes(id) ? value.filter((v) => v !== id) : [...value, id]);
  }

  const selectedProducts = products.filter((p) => value.includes(p.id));

  return (
    <div className="flex flex-col gap-2">
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            type="button"
            variant="outline"
            disabled={disabled}
            className={cn(
              "h-11 w-full justify-between bg-input font-normal shadow-soft hover:bg-card",
              value.length === 0 && "text-muted-foreground",
            )}
          >
            <span className="flex min-w-0 items-center gap-2">
              <Bag2 set="light" size={18} primaryColor="#828282" />
              <span className="truncate text-start">
                {isPending
                  ? "در حال بارگذاری محصولات..."
                  : value.length > 0
                    ? `${value.length.toLocaleString("fa-IR")} محصول انتخاب شده`
                    : "انتخاب محصولات مرتبط"}
              </span>
            </span>
            <ChevronDown set="light" size={18} primaryColor="#828282" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="p-0">
          <Command>
            <CommandInput placeholder="جستجوی محصول..." />
            <CommandList>
              <CommandEmpty>محصولی یافت نشد.</CommandEmpty>
              <CommandGroup>
                {products.map((product) => {
                  const isSelected = value.includes(product.id);
                  return (
                    <CommandItem
                      key={product.id}
                      value={product.name}
                      onSelect={() => toggle(product.id)}
                    >
                      <span className="flex-1 truncate">{product.name}</span>
                      {isSelected && <TickSquare set="bold" size={16} primaryColor="#C22026" />}
                    </CommandItem>
                  );
                })}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
      {selectedProducts.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {selectedProducts.map((product) => (
            <Badge key={product.id} variant="neutral" className="gap-1 pe-1">
              <span className="truncate">{product.name}</span>
              <button
                type="button"
                className="rounded-md p-0.5 text-muted-foreground transition-colors hover:text-destructive"
                onClick={() => toggle(product.id)}
                aria-label={`حذف ${product.name}`}
                disabled={disabled}
              >
                ×
              </button>
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}
