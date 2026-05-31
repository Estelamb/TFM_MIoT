import { cn } from "@/lib/utils";

export function StatusDot({ status, className }: { status: string; className?: string }) {
  return <span className={cn("status-dot", status, className)} />;
}
