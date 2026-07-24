import * as React from "react";

import { cn } from "@/lib/utils";

export type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement>;

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        className={cn(
          "flex min-h-24 w-full rounded-lg bg-input px-4 py-3 text-sm text-foreground shadow-soft transition-all duration-200 placeholder:text-muted-foreground",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40 focus-visible:bg-card",
          "disabled:cursor-not-allowed disabled:opacity-50",
          "aria-[invalid=true]:ring-2 aria-[invalid=true]:ring-destructive/50",
          className,
        )}
        {...props}
      />
    );
  },
);
Textarea.displayName = "Textarea";

export { Textarea };
