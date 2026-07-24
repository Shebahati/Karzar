import * as React from "react";

import { cn } from "@/lib/utils";
import { Label } from "@/components/ui/label";

interface FieldProps {
  label?: string;
  htmlFor?: string;
  required?: boolean;
  hint?: string;
  error?: string;
  className?: string;
  children: React.ReactNode;
}

/**
 * Layout primitive for a single form control: label, control slot, optional
 * hint, and validation error. Keeps the product form declarative and RTL-safe.
 */
export function Field({
  label,
  htmlFor,
  required,
  hint,
  error,
  className,
  children,
}: FieldProps) {
  return (
    <div className={cn("flex flex-col gap-2", className)}>
      {label && (
        <Label htmlFor={htmlFor}>
          {label}
          {required && <span className="ms-1 text-primary">*</span>}
        </Label>
      )}
      {children}
      {error ? (
        <p className="text-xs font-medium text-destructive">{error}</p>
      ) : hint ? (
        <p className="text-xs text-muted-foreground">{hint}</p>
      ) : null}
    </div>
  );
}
