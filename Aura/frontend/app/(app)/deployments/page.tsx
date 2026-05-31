"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getDeployments, getDevices, getModels, getScripts, createDeployment } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { StatusDot } from "@/components/ui/StatusDot";
import { Modal } from "@/components/ui/Modal";
import { EmptyState } from "@/components/ui/EmptyState";
import { HW_LABELS, fmtDate, fmtRelative } from "@/lib/utils";
import { Rocket, Plus, AlertTriangle } from "lucide-react";

const STATUS_BADGE: Record<string, "accent" | "success" | "danger" | "muted" | "info"> = {
  running: "accent", sent: "info", pending: "muted", failed: "danger",
};

export default function DeploymentsPage() {
  const qc = useQueryClient();
  const { data: deployments = [], isLoading } = useQuery({ queryKey: ["deployments"], queryFn: getDeployments, refetchInterval: 5000 });
  const { data: devices = [] }  = useQuery({ queryKey: ["devices"],  queryFn: getDevices });
  const { data: models = [] }   = useQuery({ queryKey: ["models"],   queryFn: getModels });
  const { data: scripts = [] }  = useQuery({ queryKey: ["scripts"],  queryFn: getScripts });
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ device_id: "", model_id: "", script_id: "" });
  const [deployErr, setDeployErr] = useState("");

  const readyModels = models.filter(m => m.compile_status === "ready");

  const deploy = useMutation({
    mutationFn: () => createDeployment(form),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["deployments"] }); setOpen(false); setDeployErr(""); setForm({ device_id: "", model_id: "", script_id: "" }); },
    onError: (e: any) => setDeployErr(e?.response?.data?.detail || "Deployment failed"),
  });

  const deviceOptions = devices.map(d => ({ value: d.id, label: `${d.name} (${HW_LABELS[d.hardware_type] || d.hardware_type})` }));
  const modelOptions  = readyModels.map(m => ({ value: m.id, label: m.name }));
  const scriptOptions = scripts.map(s => ({ value: s.id, label: s.name }));

  return (
    <div className="max-w-4xl mx-auto space-y-5 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-aura-text">Deployments</h2>
          <p className="text-xs text-aura-dim mt-0.5">Deploy models and scripts to edge devices</p>
        </div>
        <Button onClick={() => setOpen(true)}><Plus size={14} />New deployment</Button>
      </div>

      {isLoading ? (
        <div className="text-center py-16 text-aura-dim text-sm">Loading…</div>
      ) : deployments.length === 0 ? (
        <Card><EmptyState icon={Rocket} title="No deployments yet" description="Create a deployment to send a model to an edge device." action={<Button onClick={() => setOpen(true)}><Plus size={14} />New deployment</Button>} /></Card>
      ) : (
        <div className="grid gap-3">
          {deployments.map(d => {
            const device = devices.find(dev => dev.id === d.device_id);
            const model  = models.find(m => m.id === d.model_id);
            const script = scripts.find(s => s.id === d.script_id);
            return (
              <Card key={d.id} className={d.status === "failed" ? "border-aura-danger/30" : ""}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-aura-muted flex items-center justify-center flex-shrink-0">
                      <StatusDot status={d.status} className="w-2.5 h-2.5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono text-aura-dim">{d.id.slice(0, 12)}…</span>
                        <Badge variant={STATUS_BADGE[d.status] || "muted"}>{d.status}</Badge>
                      </div>
                      <div className="flex flex-wrap items-center gap-2 mt-1.5">
                        {device && <Badge variant="muted">📡 {device.name}</Badge>}
                        {model  && <Badge variant="muted">🧠 {model.name}</Badge>}
                        {script && <Badge variant="muted">⚡ {script.name}</Badge>}
                      </div>
                      {d.error_msg && (
                        <div className="flex items-center gap-1 mt-1.5">
                          <AlertTriangle size={11} className="text-aura-danger flex-shrink-0" />
                          <p className="text-xs text-aura-danger font-mono">{d.error_msg.slice(0, 80)}</p>
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="text-right hidden sm:block flex-shrink-0 ml-4">
                    <p className="text-xs text-aura-dim">{fmtRelative(d.created_at)}</p>
                    {d.running_at && <p className="text-xs text-aura-success font-mono mt-0.5">Running {fmtRelative(d.running_at)}</p>}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      <Modal open={open} onClose={() => { setOpen(false); setDeployErr(""); }} title="New Deployment">
        <form onSubmit={e => { e.preventDefault(); deploy.mutate(); }} className="flex flex-col gap-4">
          {deviceOptions.length === 0 ? (
            <p className="text-xs text-aura-warning">No devices registered. Register a device first.</p>
          ) : (
            <Select label="Target device" value={form.device_id} onChange={e => setForm(f => ({ ...f, device_id: e.target.value }))}
              options={[{ value: "", label: "Select device…" }, ...deviceOptions]} required />
          )}
          {modelOptions.length === 0 ? (
            <p className="text-xs text-aura-warning">No compiled models available. Upload and compile a model first.</p>
          ) : (
            <Select label="Model (compiled)" value={form.model_id} onChange={e => setForm(f => ({ ...f, model_id: e.target.value }))}
              options={[{ value: "", label: "Select model…" }, ...modelOptions]} required />
          )}
          {scriptOptions.length === 0 ? (
            <p className="text-xs text-aura-warning">No scripts available. Upload a script first.</p>
          ) : (
            <Select label="Inference script" value={form.script_id} onChange={e => setForm(f => ({ ...f, script_id: e.target.value }))}
              options={[{ value: "", label: "Select script…" }, ...scriptOptions]} required />
          )}
          {deployErr && <p className="text-xs text-aura-danger">{deployErr}</p>}
          <div className="flex gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)} className="flex-1 justify-center">Cancel</Button>
            <Button type="submit" loading={deploy.isPending}
              disabled={!form.device_id || !form.model_id || !form.script_id}
              className="flex-1 justify-center">Deploy</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
