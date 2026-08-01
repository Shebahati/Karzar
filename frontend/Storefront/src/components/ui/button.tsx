import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/**
 * Shared Storefront button — hover uses brand-tinted elevation (red/steel),
 * never a white flood or diffuse white glow. Hover-fine avoids sticky glow on touch.
 */
const buttonVariants = cva(
  [
    "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium",
    "transition-[background-color,color,box-shadow,transform,opacity,border-color] duration-200 ease-out",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 focus-visible:ring-offset-0",
    "disabled:pointer-events-none disabled:opacity-50",
    "active:scale-[0.98] active:shadow-none",
  ].join(" "),
  {
    variants: {
      variant: {
        primary:
          "bg-primary text-primary-foreground shadow-btn-rest hover-fine:bg-karzar-600 hover-fine:shadow-btn-primary hover-fine:-translate-y-px",
        outline:
          "bg-transparent text-foreground ring-1 ring-inset ring-border hover-fine:bg-steel/[0.07] hover-fine:text-foreground hover-fine:ring-steel/30 hover-fine:shadow-btn-steel",
        ghost:
          "bg-transparent text-foreground hover-fine:bg-steel/[0.09] hover-fine:text-foreground",
        soft:
          "bg-white text-foreground shadow-btn-rest ring-1 ring-inset ring-steel/10 hover-fine:bg-karzar-50 hover-fine:text-karzar-700 hover-fine:ring-primary/25 hover-fine:shadow-btn-soft hover-fine:-translate-y-px",
        muted:
          "bg-secondary text-secondary-foreground hover-fine:bg-steel/[0.12] hover-fine:text-foreground",
        destructive:
          "bg-destructive text-destructive-foreground shadow-btn-rest hover-fine:opacity-90 hover-fine:shadow-btn-primary",
      },
      size: {
        sm: "h-9 px-4",
        md: "h-11 px-6",
        lg: "h-13 px-8 text-base",
        icon: "h-11 w-11",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  ),
);
Button.displayName = "Button";

export { buttonVariants };
