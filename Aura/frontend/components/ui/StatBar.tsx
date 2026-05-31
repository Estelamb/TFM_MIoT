"use client";
import { cn } from "@/lib/utils";

export function StatBar({ value, max = 100, color = "aura-accent", label, unit = "%" }:
  { value: number; max?: number; color?: string; label?: string; unit?: string }) {
  const pct = Math.min(100, (value / max) * 100);
  const colorMap: Record<string, string> = {
    "aura-accent": "bg-aura-accent",
    "aura-success": "bg-aura-success",
    "aura-warning": "bg-aura-warning",
    "aura-danger": "bg-aura-danger",
  };
  const bar = colorMap[color] || "bg-aura-accent";
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <div className="flex justify-between items-center">
          <span className="text-xs text-aura-dim">{label}</span>
          <span className="text-xs font-mono text-aura-text">{value.toFixed(1)}{unit}</span>
        </div>
      )}
      <div className="h-1.5 bg-aura-muted rounded-full overflow-hidden">
        <div className={cn("h-full rounded-full transition-all duration-500", bar)} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
