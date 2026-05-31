"use client";
import { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getScripts, uploadScript, deleteScript, HARDWARE_TYPES } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Select } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { EmptyState } from "@/components/ui/EmptyState";
import { HW_LABELS, fmtDate } from "@/lib/utils";
import { Code2, Plus, Trash2, Upload, FileCode } from "lucide-react";

const HW_OPTIONS = HARDWARE_TYPES.map(v => ({ value: v, label: HW_LABELS[v] || v }));

export default function ScriptsPage() {
  const qc = useQueryClient();
  const { data: scripts = [], isLoading } = useQuery({ queryKey: ["scripts"], queryFn: getScripts });
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", hardware_type: "hailo8" });
  const [file, setFile] = useState<File | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const upload = useMutation({
    mutationFn: () => uploadScript(form.name, form.description, form.hardware_type, file!),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["scripts"] }); setOpen(false); setFile(null); setForm({ name: "", description: "", hardware_type: "hailo8" }); },
  });
  const remove = useMutation({
    mutationFn: (id: string) => deleteScript(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["scripts"] }),
  });

  return (
    <div className="max-w-4xl mx-auto space-y-5 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-aura-text">Scripts</h2>
          <p className="text-xs text-aura-dim mt-0.5">Pre/post-inference scripts for edge execution</p>
        </div>
        <Button onClick={() => setOpen(true)}><Plus size={14} />Upload script</Button>
      </div>

      {isLoading ? (
        <div className="text-center py-16 text-aura-dim text-sm">Loading…</div>
      ) : scripts.length === 0 ? (
        <Card><EmptyState icon={Code2} title="No scripts uploaded" description="Upload a pre/post-inference script to use in deployments." action={<Button onClick={() => setOpen(true)}><Plus size={14} />Upload script</Button>} /></Card>
      ) : (
        <div className="grid gap-3">
          {scripts.map(s => (
            <Card key={s.id} className="transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-aura-muted flex items-center justify-center flex-shrink-0">
                    <FileCode size={16} className="text-aura-accent" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-aura-text">{s.name}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant="muted">{HW_LABELS[s.hardware_type] || s.hardware_type}</Badge>
                      {s.description && <span className="text-xs text-aura-dim">{s.description}</span>}
                    </div>
                    {s.script_sha256 && <p className="text-[10px] font-mono text-aura-dim mt-1">SHA: {s.script_sha256.slice(0, 16)}…</p>}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-right hidden sm:block">
                    <p className="text-xs text-aura-dim">Uploaded</p>
                    <p className="text-xs font-mono text-aura-text">{fmtDate(s.created_at)}</p>
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => remove.mutate(s.id)} className="text-aura-dim hover:text-aura-danger"><Trash2 size={13} /></Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal open={open} onClose={() => setOpen(false)} title="Upload Script">
        <form onSubmit={e => { e.preventDefault(); if (file) upload.mutate(); }} className="flex flex-col gap-4">
          <Input label="Script name" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="e.g. yolov8-door-postprocess" required />
          <Input label="Description (optional)" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} placeholder="What this script does…" />
          <Select label="Target hardware" value={form.hardware_type} onChange={e => setForm(f => ({ ...f, hardware_type: e.target.value }))} options={HW_OPTIONS} />
          <div>
            <label className="text-xs font-medium text-aura-dim uppercase tracking-wider block mb-1.5">Script file (.py)</label>
            <div onClick={() => fileRef.current?.click()}
              className="border border-dashed border-aura-border rounded-xl p-6 flex flex-col items-center gap-2 cursor-pointer hover:border-aura-accent transition-colors">
              <Upload size={20} className="text-aura-dim" />
              <p className="text-sm text-aura-dim">
                {file ? <span className="text-aura-accent font-medium">{file.name}</span> : "Click to select .py file"}
              </p>
              <input ref={fileRef} type="file" accept=".py" className="hidden" onChange={e => setFile(e.target.files?.[0] || null)} />
            </div>
          </div>
          <div className="flex gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setOpen(false)} className="flex-1 justify-center">Cancel</Button>
            <Button type="submit" loading={upload.isPending} disabled={!file} className="flex-1 justify-center">Upload</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
