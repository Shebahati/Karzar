import * as React from "react";
import { useId } from "react";
import { cn } from "@/lib/utils";

/** Labeled form control wrapper with inline error text. Borderless inputs. */
export function Field({
  label,
  error,
  hint,
  className,
  children,
  htmlFor,
}: {
  label: string;
  error?: string;
  hint?: string;
  className?: string;
  children: React.ReactNode;
  htmlFor?: string;
}) {
  const autoId = useId();
  const controlId = htmlFor ?? autoId;
  const errorId = error ? `${controlId}-error` : undefined;
  const hintId = !error && hint ? `${controlId}-hint` : undefined;
  const describedBy = [errorId, hintId].filter(Boolean).join(" ") || undefined;

  const control = React.isValidElement(children)
    ? React.cloneElement(
        children as React.ReactElement<Record<string, unknown>>,
        {
          id: (children.props as { id?: string }).id ?? controlId,
          "aria-invalid": error ? true : undefined,
          "aria-describedby": describedBy,
        },
      )
    : children;

  return (
    <label className={cn("block", className)} htmlFor={controlId}>
      <span className="mb-1.5 block text-sm font-bold text-foreground">{label}</span>
      {control}
      {error ? (
        <span id={errorId} className="mt-1 block text-xs text-primary" role="alert">
          {error}
        </span>
      ) : hint ? (
        <span id={hintId} className="mt-1 block text-xs text-muted-foreground">
          {hint}
        </span>
      ) : null}
    </label>
  );
}

export const fieldInputClass =
  "h-12 w-full rounded-xl bg-input px-4 text-base outline-none transition-shadow focus:ring-2 focus:ring-ring/40";

/** Textareas use 16px text to avoid iOS input zoom (same as fieldInputClass). */
export const fieldTextareaClass =
  "w-full rounded-xl bg-input p-4 text-base outline-none transition-shadow focus:ring-2 focus:ring-ring/40";
