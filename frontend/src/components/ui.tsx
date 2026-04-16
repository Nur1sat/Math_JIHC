"use client";

import { type ButtonHTMLAttributes, type CSSProperties, type ReactNode } from "react";

export function cn(...parts: Array<string | false | null | undefined>) {
  return parts.filter(Boolean).join(" ");
}

export function MaterialIcon({
  icon,
  className,
  fill = false
}: {
  icon: string;
  className?: string;
  fill?: boolean;
}) {
  return (
    <span
      className={cn("material-symbols-outlined", className)}
      style={
        fill
          ? ({
              fontVariationSettings: "'FILL' 1, 'wght' 500, 'GRAD' 0, 'opsz' 24"
            } as CSSProperties)
          : undefined
      }
    >
      {icon}
    </span>
  );
}

export function BrandIdentity({
  compact = false,
  light = false,
  className
}: {
  compact?: boolean;
  light?: boolean;
  className?: string;
}) {
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <img
        alt="Math_JIHC logo"
        className={compact ? "h-9 w-9 object-contain" : "h-11 w-11 object-contain"}
        src="/math_jihc-logo.svg"
      />
      <div className="min-w-0">
        <p className={cn("font-black tracking-tight", compact ? "text-lg" : "text-2xl", light ? "text-white" : "text-green-800")}>
          Math_JIHC
        </p>
      </div>
    </div>
  );
}

export function LoadingPanel({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="rounded-[2rem] border border-outline-variant/30 bg-surface-container-lowest p-8 shadow-soft">
      <div className="flex items-center gap-3 text-secondary">
        <div className="h-3 w-3 animate-pulse rounded-full bg-primary" />
        <p className="text-sm font-semibold">{label}</p>
      </div>
    </div>
  );
}

export function ErrorPanel({
  message,
  action
}: {
  message: string;
  action?: ReactNode;
}) {
  return (
    <div className="rounded-[2rem] border border-error/20 bg-error-container p-6 text-on-error-container shadow-soft">
      <div className="flex items-start gap-3">
        <MaterialIcon className="text-error" icon="warning" fill />
        <div className="space-y-3">
          <p className="font-semibold">{message}</p>
          {action}
        </div>
      </div>
    </div>
  );
}

export function ShellFooter() {
  return (
    <footer className="w-full border-t border-slate-200/50 bg-slate-100 py-8">
      <div className="mx-auto flex max-w-7xl items-center justify-center px-8 text-sm text-slate-500">
        <p>© 2026 Math_JIHC</p>
      </div>
    </footer>
  );
}

export function PrimaryButton({
  children,
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-full bg-primary px-6 py-3 font-bold text-on-primary shadow-lg shadow-primary/20 transition-all hover:bg-primary-container active:scale-95",
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
