"use client";
import { usePathname } from "next/navigation";

const TITLES: Record<string, string> = {
  "/dashboard":   "Overview",
  "/devices":     "Devices",
  "/models":      "Models",
  "/scripts":     "Scripts",
  "/deployments": "Deployments",
  "/monitoring":  "Monitoring",
};

export function TopBar() {
  const path = usePathname();
  const title = Object.entries(TITLES).find(([k]) => path.startsWith(k))?.[1] || "AURA";
  return (
    <header className="h-14 border-b border-aura-border bg-aura-surface/80 backdrop-blur-md flex items-center px-6 gap-4">
      <h1 className="text-sm font-semibold text-aura-text">{title}</h1>
      <div className="flex-1" />
      <div className="flex items-center gap-2 text-xs text-aura-dim font-mono">
        <span className="status-dot online" />
        <span>Connected</span>
      </div>
    </header>
  );
}
