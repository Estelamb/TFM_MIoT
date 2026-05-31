import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";

export function EmptyState({ icon: Icon, title, description, action, className }:
  { icon: LucideIcon; title: string; description?: string; action?: React.ReactNode; className?: string }) {
  return (
    <div className={cn("flex flex-col items-center justify-center py-16 gap-3 text-center", className)}>
      <div className="w-12 h-12 rounded-xl bg-aura-muted flex items-center justify-center">
        <Icon size={20} className="text-aura-dim" />
      </div>
      <div>
        <p className="text-sm font-medium text-aura-text">{title}</p>
        {description && <p className="text-xs text-aura-dim mt-1">{description}</p>}
      </div>
      {action}
    </div>
  );
}
