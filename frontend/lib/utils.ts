import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)); }

export function fmtDate(iso?: string): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("es-ES", { dateStyle: "short", timeStyle: "short" }).format(new Date(iso));
}

export function fmtRelative(iso?: string): string {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60) return `hace ${s}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `hace ${m}m`;
  const h = Math.floor(m / 60);
  if (h < 24) return `hace ${h}h`;
  return fmtDate(iso);
}

export const HW_LABELS: Record<string, string> = {};

export const STATUS_COLORS: Record<string, string> = {
  online: "text-aura-success", offline: "text-aura-dim",
  running: "text-aura-accent", compiling: "text-aura-warning",
  failed: "text-aura-danger", pending: "text-aura-dim", sent: "text-aura-info",
  ready: "text-aura-success",
};
