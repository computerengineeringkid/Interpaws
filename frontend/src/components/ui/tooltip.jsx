"use client";

import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { cn } from "@/lib/utils";

function TooltipProvider({ children, ...props }) {
  return (
    <TooltipPrimitive.Provider delayDuration={150} {...props}>
      {children}
    </TooltipPrimitive.Provider>
  );
}

function Tooltip({ children, ...props }) {
  return <TooltipPrimitive.Root {...props}>{children}</TooltipPrimitive.Root>;
}

const TooltipTrigger = TooltipPrimitive.Trigger;

function TooltipContent({ className, sideOffset = 6, ...props }) {
  return (
    <TooltipPrimitive.Content
      sideOffset={sideOffset}
      className={cn(
        "z-50 overflow-hidden rounded-md border bg-popover px-3 py-1.5 text-xs text-popover-foreground shadow-md animate-in fade-in-0 zoom-in-95",
        className
      )}
      {...props}
    />
  );
}

export { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider };
