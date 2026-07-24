import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-bold leading-none transition-colors",
  {
    variants: {
      variant: {
        default: "bg-accent text-accent-foreground",
        neutral: "bg-secondary text-secondary-foreground",
        success: "bg-success/12 text-success",
        warning: "bg-warning/15 text-warning-foreground",
        danger: "bg-destructive/10 text-destructive",
        outline: "ring-1 ring-inset ring-border text-muted-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
