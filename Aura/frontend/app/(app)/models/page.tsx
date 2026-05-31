"use client";
import { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getModels, uploadModel, deleteModel, HARDWARE_TYPES } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Select } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { EmptyState } from "@/components/ui/EmptyState";
import { HW_LABELS, fmtDate } from "@/lib/utils";
import { Brain, Plus, Trash2, Upload, CheckCircle, XCircle, Loader2, Clock } from "lucide-react";

const HW_OPTIONS = HARDWARE_TYPES.map(v => ({ value: v, label: HW_LABELS[v] || v }));
const STATUS_CONFIG = {
  ready:     { icon: CheckCircle, color: "text-aura-success", badge: "success" as const },
  compiling: { icon: Loader2,     color: "text-aura-warning animate-spin", badge: "warning" as const },
  failed:    { icon: XCircle,     color: "text-aura-danger",  badge: "danger"  as const },
  pending:   { icon: Clock,       color: "text-aura-dim",     badge: "muted"   as const },
};

export default function ModelsPage() {
  const qc = useQueryClient();
  const { data: models = [], isLoading } = useQuery({ queryKey: ["models"], queryFn: getModels, refetchInterval: 5000 });
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", hardware_type: "hailo8", compile: true });
  const [file, setFile] = useState<File | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const upload = useMutation({
    mutationFn: () => uploadModel(form.name, form.description, form.hardware_type, file!, form.compile),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["models"] }); setOpen(false); setFile(null); setForm({ name: "", description: "", hardware_type: "hailo8", compile: true }); },
  });
  const remove = useMutation({
    mutationFn: (id: string) => deleteModel(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["models"] }),
  });

  return (
    <div className="max-w-4xl mx-auto space-y-5 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-aura-text">Models</h2>
          <p className="text-xs text-aura-dim mt-0.5">Upload and compile YOLOv8 models for edge hardware</p>
        </div>
        <Button onClick={() => setOpen(true)}><Plus size={14} />Upload model</Button>
      </div>

      {isLoading ? (
        <div className="text-center py-16 text-aura-dim text-sm">Loading…</div>
      ) : models.length === 0 ? (
        <Card><EmptyState icon={Brain} title="No models uploaded" description="Upload a .pt model to compile it for your hardware." action={<Button onClick={() => setOpen(true)}><Plus size={14} />Upload model</Button>} /></Card>
      ) : (
        <div className="grid gap-3">
          {models.map(m => {
            const cfg = STATUS_CONFIG[m.compile_status] || STATUS_CONFIG.pending;
            const StatusIcon = cfg.icon;
            return (
              <Card key={m.id} className="transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-aura-muted flex items-center justify-center flex-shrink-0">
                      <StatusIcon size={16} className={cfg.color} />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-aura-text">{m.name}</p>
                      <div className="flex items-center gap-2 mt-1">
                        {m.hardware_type && <Badge variant="muted">{HW_LABELS[m.hardware_type] || m.hardware_type}</Badge>}
                        <Badge variant={cfg.badge}>{m.compile_status}</Badge>
                        {m.description && <span className="text-xs text-aura-dim">{m.description}</span>}
                      </div>
                      {m.compile_error && <p className="text-xs text-aura-danger mt-1 font-mono">{m.compile_error.slice(0, 80)}…</p>}
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-right hidden sm:block">
                      <p className="text-xs text-aura-dim">Uploaded</p>
                      <p className="text-xs font-mono text-aura-text">{fmtDate(m.created_at)}</p>
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => remove.mutate(m.id)} className="text-aura-dim hover:text-aura-danger"><Trash2 size={13} /></Button>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      <Modal open={open} onClose={() => setOpen(false)} title="Upload Model">
        <form onSubmit={e => { e.preventDefault(); if (file) upload.mutate(); }} className="flex flex-col gap-4">
          <Input label="Model name" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="e.g. yolov8n-door-detector" required />
          <Input label="Description (optional)" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} placeholder="Brief description…" />
          <Select label="Target hardware" value={form.hardware_type} onChange={e => setForm(f => ({ ...f, hardware_type: e.target.value }))} options={HW_OPTIONS} />
          {/* File drop zone */}
          <div>
            <label className="text-xs font-medium text-aura-dim uppercase tracking-wider block mb-1.5">Model file (.pt)</label>
            <div onClick={() => fileRef.current?.click()}
              className="border border-dashed border-aura-border rounded-xl p-6 flex flex-col items-center gap-2 cursor-pointer hover:border-aura-accent transition-colors">
              <Upload size={20} className="text-aura-dim" />
              <p className="text-sm text-aura-dim">
                {file ? <span className="text-aura-accent font-medium">{file.name}</span> : "Click to select .pt file"}
              </p>
              <input ref={fileRef} type="file" accept=".pt" className="hidden" onChange={e => setFile(e.target.files?.[0] || null)} />
            </div>
          </div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={form.compile} onChange={e => setForm(f => ({ ...f, compile: e.target.checked }))}
              className="w-4 h-4 rounded accent-aura-accent" />
            <span className="text-sm text-aura-text">Compile automatically after upload</span>
          </label>
          <div className="flex gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)} className="flex-1 justify-center">Cancel</Button>
            <Button type="submit" loading={upload.isPending} disabled={!file} className="flex-1 justify-center">Upload</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
