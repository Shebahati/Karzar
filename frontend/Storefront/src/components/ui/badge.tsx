import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium leading-none",
  {
    variants: {
      variant: {
        primary: "bg-primary text-primary-foreground",
        accent: "bg-accent text-accent-foreground",
        success: "bg-success/12 text-success",
        warning: "bg-warning/15 text-warning-foreground",
        muted: "bg-muted text-muted-foreground",
        glass: "glass text-foreground shadow-soft",
      },
    },
    defaultVariants: { variant: "muted" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
