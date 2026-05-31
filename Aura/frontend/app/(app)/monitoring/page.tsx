"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  getMonitoringStates, getDeviceState, getInferenceResults,
  getDevices, getModels,
} from "@/lib/api";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { StatusDot } from "@/components/ui/StatusDot";
import { StatBar } from "@/components/ui/StatBar";
import { EmptyState } from "@/components/ui/EmptyState";
import { HW_LABELS, fmtRelative, fmtDate } from "@/lib/utils";
import { Activity, MemoryStick, Zap, ChevronDown, ChevronUp } from "lucide-react";

function DeviceMonitorCard({ deviceId }: { deviceId: string }) {
  const [expanded, setExpanded] = useState(false);

  const { data: devices = [] } = useQuery({ queryKey: ["devices"], queryFn: getDevices });
  const { data: models = [] }  = useQuery({ queryKey: ["models"],  queryFn: getModels });
  const { data: state }        = useQuery({
    queryKey: ["monitoring", deviceId],
    queryFn: () => getDeviceState(deviceId),
    refetchInterval: 5000,
  });
  const { data: results = [] } = useQuery({
    queryKey: ["inference", deviceId],
    queryFn: () => getInferenceResults(deviceId, 10),
    enabled: expanded,
    refetchInterval: expanded ? 5000 : false,
  });

  const device     = devices.find(d => d.id === deviceId);
  const activeModel = models.find(m => m.id === state?.active_model_id);

  if (!state) return null;

  return (
    <Card className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <StatusDot status={state.status} />
          <div>
            <p className="text-sm font-semibold text-aura-text">{device?.name || deviceId}</p>
            {device && (
              <p className="text-xs text-aura-dim font-mono">
                {HW_LABELS[device.hardware_type] || device.hardware_type}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={state.status === "online" ? "success" : "muted"}>{state.status}</Badge>
          <span className="text-xs text-aura-dim">{fmtRelative(state.last_seen_at)}</span>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-3">
        <StatBar
          value={state.cpu_percent} label="CPU"
          color={state.cpu_percent > 80 ? "aura-danger" : "aura-accent"}
        />
        <StatBar
          value={state.ram_percent} label="RAM"
          color={state.ram_percent > 80 ? "aura-warning" : "aura-success"}
        />
      </div>
      <div className="flex items-center gap-4 text-xs text-aura-dim">
        <span className="flex items-center gap-1">
          <MemoryStick size={11} />
          {state.ram_used_mb.toFixed(0)} MB used
        </span>
        {state.active_deployment_id && (
          <span className="flex items-center gap-1">
            <Zap size={11} className="text-aura-accent" />
            Deployment active
          </span>
        )}
      </div>

      {/* Active model */}
      {activeModel && (
        <div className="bg-aura-muted/40 rounded-lg p-3 border border-aura-border text-xs space-y-1">
          <p className="text-aura-dim">Active model</p>
          <p className="font-medium text-aura-text">{activeModel.name}</p>
          <p className="font-mono text-aura-dim">{activeModel.hardware_type}</p>
        </div>
      )}

      {/* Inference results toggle */}
      <button
        onClick={() => setExpanded(e => !e)}
        className="flex items-center gap-1.5 text-xs text-aura-dim hover:text-aura-text transition-colors w-full pt-2 border-t border-aura-border"
      >
        {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        {expanded ? "Hide" : "Show"} last inference results
      </button>

      {expanded && (
        <div className="space-y-2 animate-slide-up">
          {results.length === 0 ? (
            <p className="text-xs text-aura-dim text-center py-4">No inference results yet</p>
          ) : (
            results.map((r, i) => {
              let parsed: any[] = [];
              try { parsed = JSON.parse(r.result_json); } catch {}
              const isArray = Array.isArray(parsed);
              return (
                <div key={i} className="bg-aura-bg rounded-lg p-3 border border-aura-border">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-mono text-aura-dim">{fmtDate(r.timestamp)}</span>
                    {isArray && <Badge variant="muted">{parsed.length} detections</Badge>}
                  </div>
                  {isArray && parsed.length > 0 ? (
                    <div className="flex flex-wrap gap-1.5">
                      {parsed.slice(0, 5).map((det: any, j: number) => (
                        <Badge key={j} variant="accent" className="text-[10px]">
                          {det.class} {(det.confidence * 100).toFixed(0)}%
                        </Badge>
                      ))}
                      {parsed.length > 5 && (
                        <Badge variant="muted" className="text-[10px]">+{parsed.length - 5} more</Badge>
                      )}
                    </div>
                  ) : (
                    <p className="text-[10px] font-mono text-aura-dim truncate">
                      {r.result_json.slice(0, 100)}
                    </p>
                  )}
                </div>
              );
            })
          )}
        </div>
      )}
    </Card>
  );
}

export default function MonitoringPage() {
  const { data: states = [], isLoading } = useQuery({
    queryKey: ["monitoring"],
    queryFn: getMonitoringStates,
    refetchInterval: 5000,
  });
  const { data: devices = [] } = useQuery({ queryKey: ["devices"], queryFn: getDevices });

  const devicesWithoutData = devices.filter(d => !states.find(s => s.device_id === d.id));

  return (
    <div className="max-w-4xl mx-auto space-y-5 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-aura-text">Monitoring</h2>
          <p className="text-xs text-aura-dim mt-0.5">
            Live telemetry and inference results from edge devices
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-aura-dim font-mono">
          <Activity size={13} className="animate-pulse text-aura-accent" />
          Live · 5s refresh
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-16 text-aura-dim text-sm">Loading…</div>
      ) : states.length === 0 ? (
        <Card>
          <EmptyState
            icon={Activity}
            title="No device data"
            description="Devices send telemetry automatically over MQTT when the edge agent is running."
          />
        </Card>
      ) : (
        <div className="grid gap-4">
          {states.map(s => (
            <DeviceMonitorCard key={s.device_id} deviceId={s.device_id} />
          ))}
        </div>
      )}

      {devicesWithoutData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Offline devices</CardTitle>
          </CardHeader>
          <div className="space-y-2">
            {devicesWithoutData.map(d => (
              <div
                key={d.id}
                className="flex items-center justify-between py-2 border-b border-aura-border last:border-0"
              >
                <div className="flex items-center gap-2">
                  <StatusDot status="offline" />
                  <span className="text-sm text-aura-text">{d.name}</span>
                  <Badge variant="muted">{HW_LABELS[d.hardware_type] || d.hardware_type}</Badge>
                </div>
                <span className="text-xs text-aura-dim">No data received</span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
