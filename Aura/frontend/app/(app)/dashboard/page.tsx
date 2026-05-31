"use client";
import { useQuery } from "@tanstack/react-query";
import { getDevices, getModels, getScripts, getDeployments, getMonitoringStates } from "@/lib/api";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { StatusDot } from "@/components/ui/StatusDot";
import { Badge } from "@/components/ui/Badge";
import { StatBar } from "@/components/ui/StatBar";
import { HW_LABELS, fmtRelative } from "@/lib/utils";
import { Cpu, Brain, Code2, Rocket, Activity, AlertTriangle } from "lucide-react";
import Link from "next/link";

function StatCard({ label, value, icon: Icon, href }: { label: string; value: number; icon: React.ElementType; href: string }) {
  return (
    <Link href={href}>
      <Card className="hover:border-aura-accent/50 cursor-pointer group transition-all">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-2xl font-bold font-mono text-aura-text">{value}</p>
            <p className="text-xs text-aura-dim mt-1">{label}</p>
          </div>
          <div className="w-10 h-10 rounded-xl bg-aura-muted flex items-center justify-center group-hover:bg-aura-accent/20 transition-colors">
            <Icon size={18} className="text-aura-dim group-hover:text-aura-accent transition-colors" />
          </div>
        </div>
      </Card>
    </Link>
  );
}

export default function DashboardPage() {
  const { data: devices = [] }     = useQuery({ queryKey: ["devices"],     queryFn: getDevices });
  const { data: models = [] }      = useQuery({ queryKey: ["models"],      queryFn: getModels });
  const { data: scripts = [] }     = useQuery({ queryKey: ["scripts"],     queryFn: getScripts });
  const { data: deployments = [] } = useQuery({ queryKey: ["deployments"], queryFn: getDeployments });
  const { data: states = [] }      = useQuery({ queryKey: ["monitoring"],  queryFn: getMonitoringStates, refetchInterval: 5000 });

  const online  = devices.filter(d => d.status === "online").length;
  const running = deployments.filter(d => d.status === "running").length;
  const failed  = deployments.filter(d => d.status === "failed").length;

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-fade-in">
      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Devices"     value={devices.length}     icon={Cpu}      href="/devices" />
        <StatCard label="Models"      value={models.length}      icon={Brain}    href="/models" />
        <StatCard label="Scripts"     value={scripts.length}     icon={Code2}    href="/scripts" />
        <StatCard label="Deployments" value={deployments.length} icon={Rocket}   href="/deployments" />
      </div>

      {/* Status summary */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <div className="flex items-center gap-2 mb-1">
            <StatusDot status="online" />
            <span className="text-xs text-aura-dim">Online devices</span>
          </div>
          <p className="text-xl font-bold font-mono text-aura-success">{online} <span className="text-sm font-normal text-aura-dim">/ {devices.length}</span></p>
        </Card>
        <Card>
          <div className="flex items-center gap-2 mb-1">
            <StatusDot status="running" />
            <span className="text-xs text-aura-dim">Running deployments</span>
          </div>
          <p className="text-xl font-bold font-mono text-aura-accent">{running}</p>
        </Card>
        <Card className={failed > 0 ? "border-aura-danger/30" : ""}>
          <div className="flex items-center gap-2 mb-1">
            {failed > 0 ? <AlertTriangle size={12} className="text-aura-danger" /> : <StatusDot status="online" />}
            <span className="text-xs text-aura-dim">Failed deployments</span>
          </div>
          <p className={`text-xl font-bold font-mono ${failed > 0 ? "text-aura-danger" : "text-aura-dim"}`}>{failed}</p>
        </Card>
      </div>

      {/* Live device states */}
      {states.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Live Device Telemetry</CardTitle>
            <Activity size={14} className="text-aura-dim animate-pulse" />
          </CardHeader>
          <div className="space-y-5">
            {states.map(s => (
              <div key={s.device_id} className="border-t border-aura-border pt-4 first:border-0 first:pt-0">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <StatusDot status={s.status} />
                    <span className="text-sm font-medium text-aura-text font-mono">{s.device_id}</span>
                  </div>
                  <span className="text-xs text-aura-dim">{fmtRelative(s.last_seen_at)}</span>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <StatBar value={s.cpu_percent} label="CPU" color={s.cpu_percent > 80 ? "aura-danger" : "aura-accent"} />
                  <StatBar value={s.ram_percent} label="RAM" color={s.ram_percent > 80 ? "aura-warning" : "aura-success"} />
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Recent deployments */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Deployments</CardTitle>
          <Link href="/deployments" className="text-xs text-aura-accent hover:underline">View all</Link>
        </CardHeader>
        {deployments.length === 0 ? (
          <p className="text-xs text-aura-dim text-center py-8">No deployments yet</p>
        ) : (
          <div className="space-y-2">
            {deployments.slice(0, 5).map(d => (
              <div key={d.id} className="flex items-center justify-between py-2 border-b border-aura-border last:border-0">
                <div className="flex items-center gap-2">
                  <StatusDot status={d.status} />
                  <span className="text-xs font-mono text-aura-dim">{d.id.slice(0, 8)}…</span>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant={d.status === "running" ? "accent" : d.status === "failed" ? "danger" : "muted"}>
                    {d.status}
                  </Badge>
                  <span className="text-xs text-aura-dim">{fmtRelative(d.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
