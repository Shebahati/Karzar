"use client";

import { Delete, Plus } from "react-iconly";

import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { TagInput } from "@/components/ui/tag-input";
import { Textarea } from "@/components/ui/textarea";
import { ARTICLE_BLOCK_TYPE_LABELS, ARTICLE_BLOCK_TYPES } from "@/types/cms";
import type { ArticleBlock, ArticleBlockType } from "@/types/cms";

interface ArticleBlocksEditorProps {
  blocks: ArticleBlock[];
  onChange: (blocks: ArticleBlock[]) => void;
  disabled?: boolean;
  errors?: Record<number, string>;
}

/** Editable list of article body blocks (paragraph/heading/quote text or list items). */
export function ArticleBlocksEditor({ blocks, onChange, disabled, errors }: ArticleBlocksEditorProps) {
  function updateBlock(index: number, next: Partial<ArticleBlock>) {
    onChange(blocks.map((block, i) => (i === index ? { ...block, ...next } : block)));
  }

  function removeBlock(index: number) {
    onChange(blocks.filter((_, i) => i !== index));
  }

  function addBlock() {
    onChange([...blocks, { type: "paragraph", text: "" }]);
  }

  function changeType(index: number, type: ArticleBlockType) {
    if (type === "list") {
      updateBlock(index, { type, items: blocks[index].items ?? [], text: undefined });
    } else {
      updateBlock(index, { type, text: blocks[index].text ?? "", items: undefined });
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {blocks.length === 0 && (
        <p className="rounded-xl bg-muted/40 p-4 text-center text-xs text-muted-foreground">
          هنوز بلاکی برای محتوای مقاله اضافه نشده است.
        </p>
      )}
      {blocks.map((block, index) => (
        <div key={index} className="flex flex-col gap-3 rounded-xl bg-[#F7F7F7] p-4">
          <div className="flex items-center justify-between gap-3">
            <div className="w-40">
              <Select
                value={block.type}
                onValueChange={(v) => changeType(index, v as ArticleBlockType)}
              >
                <SelectTrigger disabled={disabled}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ARTICLE_BLOCK_TYPES.map((type) => (
                    <SelectItem key={type} value={type}>
                      {ARTICLE_BLOCK_TYPE_LABELS[type]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              disabled={disabled}
              aria-label="حذف بلاک"
              className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
              onClick={() => removeBlock(index)}
            >
              <Delete set="light" size={18} primaryColor="currentColor" />
            </Button>
          </div>

          {block.type === "list" ? (
            <Field error={errors?.[index]}>
              <TagInput
                value={block.items ?? []}
                onChange={(items) => updateBlock(index, { items })}
                disabled={disabled}
                placeholder="مورد را تایپ و Enter بزنید"
              />
            </Field>
          ) : (
            <Field error={errors?.[index]}>
              <Textarea
                rows={3}
                value={block.text ?? ""}
                onChange={(e) => updateBlock(index, { text: e.target.value })}
                disabled={disabled}
                placeholder={
                  block.type === "heading"
                    ? "متن تیتر..."
                    : block.type === "quote"
                      ? "متن نقل‌قول..."
                      : block.type === "image"
                        ? "آدرس یا توضیح تصویر..."
                        : "متن پاراگراف..."
                }
              />
            </Field>
          )}
        </div>
      ))}

      <Button type="button" variant="outline" size="sm" disabled={disabled} onClick={addBlock}>
        <Plus set="bold" size={16} primaryColor="#C22026" />
        افزودن بلاک
      </Button>
    </div>
  );
}
