"use client";

import { useState, type KeyboardEvent } from "react";
import { CloseSquare, Plus } from "react-iconly";

import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface TagInputProps {
  value: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
  disabled?: boolean;
  "aria-invalid"?: boolean;
}

/** Multi-string tag input for feature detail arrays (e.g. button names). */
export function TagInput({
  value,
  onChange,
  placeholder = "مقدار را تایپ و Enter بزنید",
  disabled,
  ...aria
}: TagInputProps) {
  const [draft, setDraft] = useState("");

  function addTag(raw: string) {
    const next = raw.trim();
    if (!next) return;
    if (value.some((tag) => tag.toLowerCase() === next.toLowerCase())) {
      setDraft("");
      return;
    }
    onChange([...value, next]);
    setDraft("");
  }

  function removeTag(index: number) {
    onChange(value.filter((_, i) => i !== index));
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      event.preventDefault();
      addTag(draft);
    }
    if (event.key === "Backspace" && !draft && value.length > 0) {
      onChange(value.slice(0, -1));
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex gap-2">
        <Input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          aria-invalid={aria["aria-invalid"]}
          className="flex-1"
        />
        <Button
          type="button"
          variant="outline"
          size="icon"
          disabled={disabled || !draft.trim()}
          onClick={() => addTag(draft)}
          aria-label="افزودن"
        >
          <Plus set="bold" size={18} primaryColor="#C22026" />
        </Button>
      </div>
      {value.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {value.map((tag, index) => (
            <Badge key={`${tag}-${index}`} variant="neutral" className="gap-1 pe-1">
              <span>{tag}</span>
              <button
                type="button"
                className={cn(
                  "rounded-md p-0.5 text-muted-foreground transition-colors hover:text-destructive",
                  disabled && "pointer-events-none opacity-50",
                )}
                onClick={() => removeTag(index)}
                aria-label={`حذف ${tag}`}
              >
                <CloseSquare set="light" size={14} primaryColor="currentColor" />
              </button>
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}
