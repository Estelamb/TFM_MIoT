import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";

const variants = {
  primary:  "bg-aura-accent hover:bg-aura-accent-dim text-white",
  ghost:    "bg-transparent hover:bg-aura-muted text-aura-dim hover:text-aura-text",
  danger:   "bg-aura-danger/10 hover:bg-aura-danger/20 text-aura-danger border border-aura-danger/30",
  outline:  "bg-transparent border border-aura-border hover:border-aura-accent text-aura-text",
};

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof variants;
  size?: "sm" | "md" | "lg";
  loading?: boolean;
}

export function Button({ children, variant = "primary", size = "md", loading, className, disabled, ...props }: ButtonProps) {
  const sizes = { sm: "px-3 py-1.5 text-sm", md: "px-4 py-2 text-sm", lg: "px-5 py-2.5 text-base" };
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={cn("inline-flex items-center gap-2 rounded-lg font-medium transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed", variants[variant], sizes[size], className)}
    >
      {loading && <Loader2 size={14} className="animate-spin" />}
      {children}
    </button>
  );
}
