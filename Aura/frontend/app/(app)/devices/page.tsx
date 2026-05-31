"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getDevices, createDevice, deleteDevice, HARDWARE_TYPES } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Select } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { StatusDot } from "@/components/ui/StatusDot";
import { Modal } from "@/components/ui/Modal";
import { EmptyState } from "@/components/ui/EmptyState";
import { HW_LABELS, fmtDate } from "@/lib/utils";
import { Cpu, Plus, Trash2 } from "lucide-react";

const HW_OPTIONS = HARDWARE_TYPES.map(v => ({ value: v, label: HW_LABELS[v] || v }));

export default function DevicesPage() {
  const qc = useQueryClient();
  const { data: devices = [], isLoading } = useQuery({ queryKey: ["devices"], queryFn: getDevices });
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", hardware_type: "hailo8", description: "" });

  const create = useMutation({
    mutationFn: () => createDevice({ ...form, hardware_type: form.hardware_type as any }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["devices"] }); setOpen(false); setForm({ name: "", hardware_type: "hailo8", description: "" }); },
  });
  const remove = useMutation({
    mutationFn: (id: string) => deleteDevice(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["devices"] }),
  });

  return (
    <div className="max-w-4xl mx-auto space-y-5 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-aura-text">Edge Devices</h2>
          <p className="text-xs text-aura-dim mt-0.5">Manage registered edge hardware</p>
        </div>
        <Button onClick={() => setOpen(true)}><Plus size={14} />Register device</Button>
      </div>

      {isLoading ? (
        <div className="text-center py-16 text-aura-dim text-sm">Loading…</div>
      ) : devices.length === 0 ? (
        <Card><EmptyState icon={Cpu} title="No devices registered" description="Register your first edge device to get started." action={<Button onClick={() => setOpen(true)}><Plus size={14} />Register device</Button>} /></Card>
      ) : (
        <div className="grid gap-3">
          {devices.map(d => (
            <Card key={d.id} className="hover:border-aura-border/80 transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-aura-muted flex items-center justify-center flex-shrink-0">
                    <Cpu size={16} className="text-aura-dim" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <StatusDot status={d.status} />
                      <span className="text-sm font-medium text-aura-text">{d.name}</span>
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant="muted">{HW_LABELS[d.hardware_type] || d.hardware_type}</Badge>
                      {d.description && <span className="text-xs text-aura-dim">{d.description}</span>}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-right hidden sm:block">
                    <p className="text-xs text-aura-dim">Registered</p>
                    <p className="text-xs font-mono text-aura-text">{fmtDate(d.created_at)}</p>
                  </div>
                  <Badge variant={d.status === "online" ? "success" : "muted"}>{d.status}</Badge>
                  <Button variant="ghost" size="sm" onClick={() => remove.mutate(d.id)} className="text-aura-dim hover:text-aura-danger">
                    <Trash2 size={13} />
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal open={open} onClose={() => setOpen(false)} title="Register Device">
        <form onSubmit={e => { e.preventDefault(); create.mutate(); }} className="flex flex-col gap-4">
          <Input label="Device name" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="e.g. RPi5-Lab-01" required />
          <Select label="Hardware type" value={form.hardware_type} onChange={e => setForm(f => ({ ...f, hardware_type: e.target.value }))} options={HW_OPTIONS} />
          <Input label="Description (optional)" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} placeholder="Location, purpose…" />
          <div className="flex gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)} className="flex-1 justify-center">Cancel</Button>
            <Button type="submit" loading={create.isPending} className="flex-1 justify-center">Register</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
