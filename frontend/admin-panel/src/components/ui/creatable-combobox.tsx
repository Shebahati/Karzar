"use client";

import { useMemo, useState } from "react";
import { ChevronDown, TickSquare } from "react-iconly";

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

interface CreatableComboboxProps {
  value: string;
  onChange: (value: string) => void;
  options: string[];
  placeholder?: string;
  searchPlaceholder?: string;
  emptyLabel?: string;
  disabled?: boolean;
  "aria-invalid"?: boolean;
  className?: string;
}

/**
 * Searchable combobox that allows picking a suggestion or typing a custom value.
 */
export function CreatableCombobox({
  value,
  onChange,
  options,
  placeholder = "انتخاب یا تایپ...",
  searchPlaceholder = "جستجو یا مقدار جدید...",
  emptyLabel = "موردی یافت نشد — Enter برای ثبت مقدار جدید",
  disabled,
  className,
  ...aria
}: CreatableComboboxProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  const mergedOptions = useMemo(() => {
    const set = new Set(options.map((o) => o.trim()).filter(Boolean));
    if (value.trim()) set.add(value.trim());
    if (query.trim()) set.add(query.trim());
    return Array.from(set);
  }, [options, query, value]);

  function commit(next: string) {
    onChange(next.trim());
    setOpen(false);
    setQuery("");
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          disabled={disabled}
          aria-invalid={aria["aria-invalid"]}
          className={cn(
            "h-11 w-full justify-between bg-input font-normal shadow-soft hover:bg-card",
            !value && "text-muted-foreground",
            className,
          )}
        >
          <span className="truncate text-start">{value || placeholder}</span>
          <ChevronDown set="light" size={18} primaryColor="#828282" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="p-0">
        <Command shouldFilter={false}>
          <CommandInput
            placeholder={searchPlaceholder}
            value={query}
            onValueChange={setQuery}
            onKeyDown={(event) => {
              if (event.key === "Enter" && query.trim()) {
                event.preventDefault();
                commit(query);
              }
            }}
          />
          <CommandList>
            <CommandEmpty>{emptyLabel}</CommandEmpty>
            <CommandGroup>
              {mergedOptions.map((option) => (
                <CommandItem key={option} value={option} onSelect={() => commit(option)}>
                  <span className="flex-1 truncate">{option}</span>
                  {value === option && (
                    <TickSquare set="bold" size={16} primaryColor="#C22026" />
                  )}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
