import React from "react";
import clsx from "clsx";

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "default" | "outline" | "ghost" | "destructive" | "secondary";
  size?: "sm" | "md" | "lg";
};

const baseClass =
  "inline-flex items-center justify-center gap-2 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-transparent disabled:opacity-50 disabled:cursor-not-allowed";

const variantClass: Record<NonNullable<ButtonProps["variant"]>, string> = {
  default: "bg-blue-500 hover:bg-blue-600 text-white border border-white/10",
  outline: "bg-transparent text-white border border-white/20 hover:bg-white/10",
  ghost: "bg-transparent text-white hover:bg-white/10",
  destructive:
    "bg-red-500/80 hover:bg-red-600/90 text-white border border-red-400/30",
  secondary: "bg-white/10 hover:bg-white/20 text-white border border-white/10",
};

const sizeClass: Record<NonNullable<ButtonProps["size"]>, string> = {
  sm: "text-xs px-3 py-1.5",
  md: "text-sm px-4 py-2",
  lg: "text-base px-5 py-3",
};

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "md", ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={clsx(
          baseClass,
          variantClass[variant],
          sizeClass[size],
          className,
        )}
        {...props}
      />
    );
  },
);

Button.displayName = "Button";
