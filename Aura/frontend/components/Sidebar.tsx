"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { LayoutDashboard, Cpu, Brain, Code2, Rocket, Activity, LogOut } from "lucide-react";

const nav = [
  { href: "/dashboard",    label: "Overview",    icon: LayoutDashboard },
  { href: "/devices",      label: "Devices",     icon: Cpu },
  { href: "/models",       label: "Models",      icon: Brain },
  { href: "/scripts",      label: "Scripts",     icon: Code2 },
  { href: "/deployments",  label: "Deployments", icon: Rocket },
  { href: "/monitoring",   label: "Monitoring",  icon: Activity },
];

export function Sidebar() {
  const path = usePathname();
  return (
    <aside className="fixed left-0 top-0 h-full w-56 bg-aura-surface border-r border-aura-border flex flex-col z-40">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-aura-border">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-aura-accent flex items-center justify-center">
            <span className="text-white text-xs font-bold font-mono">A</span>
          </div>
          <div>
            <p className="text-sm font-semibold text-aura-text tracking-tight">AURA</p>
            <p className="text-[10px] text-aura-dim font-mono">PLATFORM PoC</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 flex flex-col gap-0.5">
        {nav.map(({ href, label, icon: Icon }) => {
          const active = path.startsWith(href);
          return (
            <Link key={href} href={href} className={cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-150",
              active
                ? "bg-aura-accent/15 text-aura-accent border border-aura-accent/20"
                : "text-aura-dim hover:text-aura-text hover:bg-aura-muted/50"
            )}>
              <Icon size={16} className="flex-shrink-0" />
              <span className="font-medium">{label}</span>
              {active && <div className="ml-auto w-1.5 h-1.5 rounded-full bg-aura-accent" />}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-3 py-4 border-t border-aura-border">
        <button
          onClick={() => { localStorage.removeItem("aura_token"); window.location.href = "/"; }}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-aura-dim hover:text-aura-danger hover:bg-aura-danger/10 transition-all"
        >
          <LogOut size={16} />
          <span>Sign out</span>
        </button>
      </div>
    </aside>
  );
}
