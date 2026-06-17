"use client";
import { useQuery } from "@tanstack/react-query";
import { getMonitoringStates, getDevices } from "@/lib/api";
import { useDataMode } from "@/hooks/useDataMode";
import { EdgeMap } from "@/components/monitoring/EdgeMap";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { StatBar } from "@/components/ui/StatBar";
import { StatusDot } from "@/components/ui/StatusDot";
import { Badge } from "@/components/ui/Badge";
import { fmtRelative } from "@/lib/utils";
import { Activity, ShieldAlert, Wifi, MemoryStick } from "lucide-react";

export default function MonitoringPage() {
  const { data: realStates = [] } = useQuery({
    queryKey: ["monitoring"],
    queryFn: getMonitoringStates,
    refetchInterval: 5000,
  });

  const { mode, demoData } = useDataMode();
  const isDemo = mode === "demo";

  const { data: realDevices = [] } = useQuery({
    queryKey: ["devices"],
    queryFn: getDevices,
  });

  const devices = isDemo ? demoData.devices : realDevices;
  const states = isDemo ? demoData.monitoringStates : realStates;

  const stats = isDemo
    ? demoData.monitoring
    : {
      activeNodes: `${states.filter((s: any) => s.status === "online").length} / ${states.length || 0}`,
      avgLatency: states.length > 0 ? "— ms" : "0 ms",
      alerts: states.filter((s: any) => s.cpu_percent > 90).length,
      cpuLoad: states.length > 0
        ? Math.round(states.reduce((acc: number, s: any) => acc + s.cpu_percent, 0) / states.length)
        : 0,
      memory: states.length > 0
        ? Math.round(states.reduce((acc: number, s: any) => acc + s.ram_percent, 0) / states.length)
        : 0,
      bandwidth: 0,
      storage: 0,
    };

  return (
    <div className="w-full max-w-[1600px] mx-auto space-y-8 animate-fade-in px-4 sm:px-6 lg:px-12 py-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl md:text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-emerald-500 mb-2 pb-1">
            Device Set Monitoring
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Real-time telemetry and edge node status across all deployment zones.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 font-mono">
          <Activity size={13} className="animate-pulse text-blue-500" />
          Live · 5s refresh
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <div className="flex items-center gap-4">
            <div className="p-3 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 rounded-xl">
              <Activity size={24} />
            </div>
            <div>
              <p className="text-sm font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Active Nodes</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.activeNodes}</p>
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center gap-4">
            <div className="p-3 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-xl">
              <Wifi size={24} />
            </div>
            <div>
              <p className="text-sm font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Avg Latency</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.avgLatency}</p>
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center gap-4">
            <div className="p-3 bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-xl">
              <ShieldAlert size={24} />
            </div>
            <div>
              <p className="text-sm font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Critical Alerts</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{stats.alerts}</p>
            </div>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Map */}
        <div className="lg:col-span-2 flex flex-col relative">
          <EdgeMap states={states} isDemo={isDemo} />
        </div>

        {/* Resource panel */}
        <div className="flex flex-col gap-6">
          <Card className="flex-1">
            <CardHeader>
              <CardTitle>Global Edge Resources</CardTitle>
            </CardHeader>
            <div className="space-y-6 mt-4">
              <StatBar label="Aggregated CPU Load" value={stats.cpuLoad} color="blue-500" unit="%" />
              <StatBar label="Global Memory Usage" value={stats.memory} color="orange-500" unit="%" />
              {(stats.bandwidth > 0 || isDemo) && (
                <StatBar label="Network Bandwidth" value={stats.bandwidth} color="emerald-500" unit="%" />
              )}
              {(stats.storage > 0 || isDemo) && (
                <StatBar label="Storage Capacity" value={stats.storage} color="red-500" unit="%" />
              )}
            </div>
          </Card>

          {/* Per-device breakdown */}
          {states.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Device Breakdown</CardTitle>
              </CardHeader>
              <div className="space-y-3 mt-2">
                {states.map((s: any) => (
                  <div key={s.device_id} className="border-b border-gray-100 dark:border-gray-800/50 pb-3 last:border-0 last:pb-0">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-1.5">
                        <StatusDot status={s.status} />
                        <span className="text-xs font-bold text-gray-700 dark:text-gray-300 truncate max-w-[120px]" title={s.device_id}>
                          {devices.find((d: any) => d.id === s.device_id)?.name || s.device_id}
                        </span>
                      </div>
                      <div className="flex items-center gap-1 text-xs text-gray-400">
                        <MemoryStick size={10} />
                        {s.ram_used_mb?.toFixed ? s.ram_used_mb.toFixed(0) : s.ram_used_mb} MB
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <StatBar value={s.cpu_percent} label="CPU" color={s.cpu_percent > 80 ? "red-500" : "blue-500"} />
                      <StatBar value={s.ram_percent} label="RAM" color={s.ram_percent > 80 ? "orange-500" : "emerald-500"} />
                    </div>
                    <p className="text-[10px] text-gray-400 mt-1">{fmtRelative(s.last_seen_at)}</p>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
