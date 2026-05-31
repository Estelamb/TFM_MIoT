import { cn } from "@/lib/utils";

const variants = {
  default:   "bg-aura-muted text-aura-text",
  accent:    "bg-aura-accent/20 text-aura-accent border border-aura-accent/30",
  success:   "bg-aura-success/15 text-aura-success border border-aura-success/30",
  warning:   "bg-aura-warning/15 text-aura-warning border border-aura-warning/30",
  danger:    "bg-aura-danger/15 text-aura-danger border border-aura-danger/30",
  info:      "bg-aura-info/15 text-aura-info border border-aura-info/30",
  muted:     "bg-transparent text-aura-dim border border-aura-border",
};

export function Badge({ children, variant = "default", className = "" }:
  { children: React.ReactNode; variant?: keyof typeof variants; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-mono font-medium", variants[variant], className)}>
      {children}
    </span>
  );
}
