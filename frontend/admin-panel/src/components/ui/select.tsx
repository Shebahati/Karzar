"use client";

import * as React from "react";
import * as SelectPrimitive from "@radix-ui/react-select";
import { ChevronDown, ChevronUp, TickSquare } from "react-iconly";

import { cn } from "@/lib/utils";

const Select = SelectPrimitive.Root;
const SelectGroup = SelectPrimitive.Group;
const SelectValue = SelectPrimitive.Value;

const SelectTrigger = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Trigger>
>(({ className, children, ...props }, ref) => (
  <SelectPrimitive.Trigger
    ref={ref}
    className={cn(
      "flex h-11 w-full items-center justify-between rounded-lg bg-input px-4 py-2 text-sm text-foreground shadow-soft transition-all duration-200",
      "data-[placeholder]:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring/40 focus:bg-card",
      "disabled:cursor-not-allowed disabled:opacity-50 aria-[invalid=true]:ring-2 aria-[invalid=true]:ring-destructive/50",
      "[&>span]:line-clamp-1 [&>span]:text-start",
      className,
    )}
    {...props}
  >
    {children}
    <SelectPrimitive.Icon asChild>
      <span className="ms-2 text-muted-foreground">
        <ChevronDown set="light" size={18} />
      </span>
    </SelectPrimitive.Icon>
  </SelectPrimitive.Trigger>
));
SelectTrigger.displayName = SelectPrimitive.Trigger.displayName;

const SelectContent = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Content>
>(({ className, children, position = "popper", ...props }, ref) => (
  <SelectPrimitive.Portal>
    <SelectPrimitive.Content
      ref={ref}
      position={position}
      className={cn(
        "relative z-50 max-h-72 min-w-[8rem] overflow-hidden rounded-xl bg-popover text-popover-foreground shadow-elevated",
        "data-[state=open]:animate-fade-in",
        position === "popper" &&
          "data-[side=bottom]:translate-y-1 data-[side=top]:-translate-y-1",
        className,
      )}
      {...props}
    >
      <SelectPrimitive.ScrollUpButton className="flex h-7 items-center justify-center text-muted-foreground">
        <ChevronUp set="light" size={16} />
      </SelectPrimitive.ScrollUpButton>
      <SelectPrimitive.Viewport
        className={cn(
          "p-1.5",
          position === "popper" && "h-[var(--radix-select-trigger-height)] w-full min-w-[var(--radix-select-trigger-width)]",
        )}
      >
        {children}
      </SelectPrimitive.Viewport>
      <SelectPrimitive.ScrollDownButton className="flex h-7 items-center justify-center text-muted-foreground">
        <ChevronDown set="light" size={16} />
      </SelectPrimitive.ScrollDownButton>
    </SelectPrimitive.Content>
  </SelectPrimitive.Portal>
));
SelectContent.displayName = SelectPrimitive.Content.displayName;

const SelectItem = React.forwardRef<
  React.ElementRef<typeof SelectPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof SelectPrimitive.Item>
>(({ className, children, ...props }, ref) => (
  <SelectPrimitive.Item
    ref={ref}
    className={cn(
      "relative flex w-full cursor-pointer select-none items-center rounded-lg py-2.5 pe-9 ps-3 text-sm outline-none transition-colors",
      "focus:bg-accent focus:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
      className,
    )}
    {...props}
  >
    <span className="absolute end-2.5 flex items-center justify-center text-primary">
      <SelectPrimitive.ItemIndicator>
        <TickSquare set="bold" size={16} />
      </SelectPrimitive.ItemIndicator>
    </span>
    <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
  </SelectPrimitive.Item>
));
SelectItem.displayName = SelectPrimitive.Item.displayName;

export {
  Select,
  SelectGroup,
  SelectValue,
  SelectTrigger,
  SelectContent,
  SelectItem,
};
