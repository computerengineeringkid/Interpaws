"use client";

import { cva } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring/50",
  {
    variants: {
      variant: {
        default: "bg-slate-900 text-white border-transparent dark:bg-slate-50 dark:text-slate-900",
        secondary: "bg-slate-100 text-slate-900 border-transparent dark:bg-slate-800 dark:text-slate-100",
        success: "bg-emerald-100 text-emerald-700 border-transparent",
        warning: "bg-amber-100 text-amber-700 border-transparent",
        danger: "bg-red-100 text-red-700 border-transparent",
        outline: "text-slate-700 dark:text-slate-200",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export function Badge({ className, variant, ...props }) {
  return (
    <span
      data-slot="badge"
      className={cn(badgeVariants({ variant, className }))}
      {...props}
    />
  );
}
