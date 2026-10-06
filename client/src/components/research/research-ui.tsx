"use client";

import React from "react";
import { cn } from "@/lib/utils";

/**
 * Shared Vercel-style primitives for /research/*.
 * Matches the rest of the app: flat near-black cards, hairline borders,
 * small semibold titles, neutral-400 secondary text, indigo reserved for
 * primary actions and "ours" highlighting.
 */

/** Standard section card shell. */
export function RCard({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border border-neutral-800 bg-neutral-900/60 p-4 text-white",
        className
      )}
    >
      {children}
    </div>
  );
}

/** Standard card header: icon tile + title + description, optional right slot. */
export function RCardHeader({
  icon,
  title,
  description,
  right,
}: {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  right?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-neutral-800 pb-3">
      <div className="flex items-center gap-2.5">
        {icon && (
          <div className="flex h-7 w-7 items-center justify-center rounded-md border border-neutral-800 bg-white/[0.03] text-neutral-400">
            {icon}
          </div>
        )}
        <div>
          <h3 className="text-sm font-medium text-white">{title}</h3>
          {description && (
            <p className="mt-0.5 text-xs text-neutral-500">{description}</p>
          )}
        </div>
      </div>
      {right && <div className="flex shrink-0 items-center gap-2">{right}</div>}
    </div>
  );
}

/** Small status badge with restrained tone colors. */
export function StatusBadge({
  tone = "neutral",
  children,
  className,
}: {
  tone?: "neutral" | "success" | "warning" | "danger" | "info";
  children: React.ReactNode;
  className?: string;
}) {
  const tones: Record<string, string> = {
    neutral: "border-neutral-700 bg-white/[0.03] text-neutral-300",
    success: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
    warning: "border-amber-500/30 bg-amber-500/10 text-amber-300",
    danger: "border-red-500/30 bg-red-500/10 text-red-300",
    info: "border-indigo-500/30 bg-indigo-500/10 text-indigo-300",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium",
        tones[tone],
        className
      )}
    >
      {children}
    </span>
  );
}

/** Pulsing status dot + label, e.g. live stream indicator. */
export function StatusDot({
  tone = "neutral",
  label,
  pulse = false,
}: {
  tone?: "neutral" | "success" | "warning" | "danger" | "info";
  label: string;
  pulse?: boolean;
}) {
  const dots: Record<string, string> = {
    neutral: "bg-neutral-500",
    success: "bg-emerald-400",
    warning: "bg-amber-400",
    danger: "bg-red-400",
    info: "bg-indigo-400",
  };
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-neutral-400">
      <span className={cn("h-1.5 w-1.5 rounded-full", dots[tone], pulse && "animate-pulse")} />
      {label}
    </span>
  );
}

/** Single metric stat: label, mono value, caption. */
export function RStat({
  label,
  value,
  caption,
  tone = "neutral",
  children,
}: {
  label: string;
  value: React.ReactNode;
  caption?: string;
  tone?: "neutral" | "success" | "warning" | "danger" | "info";
  children?: React.ReactNode;
}) {
  const values: Record<string, string> = {
    neutral: "text-white",
    success: "text-emerald-300",
    warning: "text-amber-300",
    danger: "text-red-300",
    info: "text-indigo-300",
  };
  return (
    <div className="rounded-md border border-neutral-800 bg-black/30 p-3">
      <div className="text-[11px] font-medium text-neutral-500">{label}</div>
      <div className={cn("mt-1 font-mono text-lg font-semibold tabular-nums", values[tone])}>
        {value}
      </div>
      {caption && <div className="mt-0.5 text-[11px] text-neutral-500">{caption}</div>}
      {children}
    </div>
  );
}

/** Dashed empty state used when no telemetry has streamed yet. */
export function REmpty({
  icon,
  title,
  body,
}: {
  icon?: React.ReactNode;
  title: string;
  body?: string;
}) {
  return (
    <div className="rounded-lg border border-dashed border-neutral-800 p-6 text-center">
      {icon && (
        <div className="mx-auto mb-2 flex h-8 w-8 items-center justify-center rounded-md border border-neutral-800 bg-white/[0.03] text-neutral-500">
          {icon}
        </div>
      )}
      <div className="text-[13px] font-medium text-neutral-300">{title}</div>
      {body && <p className="mx-auto mt-1 max-w-sm text-xs leading-relaxed text-neutral-500">{body}</p>}
    </div>
  );
}

/** Shared class strings for one-off className edits. */
export const rCardClass = "rounded-lg border border-neutral-800 bg-neutral-900/60 p-4 text-white";
export const rInnerTileClass = "rounded-md border border-neutral-800 bg-black/30 p-3";
export const rHeaderRowClass = "flex items-center justify-between border-b border-neutral-800 pb-3";
export const rTitleClass = "text-sm font-medium text-white";
export const rDescClass = "text-xs text-neutral-500";
