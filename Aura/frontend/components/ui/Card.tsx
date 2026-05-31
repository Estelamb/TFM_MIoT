import { cn } from "@/lib/utils";

export function Card({ children, className = "", glow }: { children: React.ReactNode; className?: string; glow?: boolean }) {
  return (
    <div className={cn("bg-aura-surface border border-aura-border rounded-xl p-5 transition-all duration-200", glow && "glow-accent", className)}>
      {children}
    </div>
  );
}

export function CardHeader({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("flex items-center justify-between mb-4", className)}>{children}</div>;
}

export function CardTitle({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <h3 className={cn("text-sm font-semibold text-aura-text tracking-wide", className)}>{children}</h3>;
}
