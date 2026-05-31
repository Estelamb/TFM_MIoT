import { cn } from "@/lib/utils";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string; error?: string;
}
export function Input({ label, error, className, ...props }: InputProps) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && <label className="text-xs font-medium text-aura-dim uppercase tracking-wider">{label}</label>}
      <input
        {...props}
        className={cn("bg-aura-bg border border-aura-border rounded-lg px-3 py-2 text-sm text-aura-text placeholder-aura-muted outline-none focus:border-aura-accent transition-colors", error && "border-aura-danger", className)}
      />
      {error && <span className="text-xs text-aura-danger">{error}</span>}
    </div>
  );
}

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string; options: { value: string; label: string }[];
}
export function Select({ label, options, className, ...props }: SelectProps) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && <label className="text-xs font-medium text-aura-dim uppercase tracking-wider">{label}</label>}
      <select
        {...props}
        className={cn("bg-aura-bg border border-aura-border rounded-lg px-3 py-2 text-sm text-aura-text outline-none focus:border-aura-accent transition-colors", className)}
      >
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}
