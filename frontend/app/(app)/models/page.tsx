"use client";
import { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getModels, uploadModel, deleteModel, HARDWARE_TYPES } from "@/lib/api";
import { useDataMode } from "@/hooks/useDataMode";
import { Card, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Select } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { HW_LABELS } from "@/lib/utils";
import {
  Brain, Plus, Trash2, Upload, CheckCircle, XCircle,
  Loader2, Clock, Layers, RotateCcw, Info,
} from "lucide-react";

const HW_OPTIONS = HARDWARE_TYPES.map(v => ({ value: v, label: HW_LABELS[v] || v }));

const STATUS_CONFIG = {
  ready:     { icon: CheckCircle, color: "text-emerald-500",              badge: "success"     as const },
  compiling: { icon: Loader2,     color: "text-yellow-500 animate-spin",  badge: "warning"     as const },
  failed:    { icon: XCircle,     color: "text-red-500",                  badge: "danger"      as const },
  pending:   { icon: Clock,       color: "text-gray-400",                 badge: "muted"       as const },
};

export default function ModelsPage() {
  const { mode, demoData } = useDataMode();
  const isDemo = mode === "demo";

  const qc = useQueryClient();
  const { data: realModels = [], isLoading } = useQuery({
    queryKey: ["models"],
    queryFn: getModels,
    refetchInterval: 5000,
  });

  const models = isDemo ? demoData.models : realModels;
  const activeDatasets = isDemo ? demoData.datasets : [];
  const activeVersions = isDemo ? demoData.yoloVersions : [];

  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", hardware_type: "hailo8", compile: true });
  const [file, setFile] = useState<File | null>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const upload = useMutation({
    mutationFn: () => uploadModel(form.name, form.description, form.hardware_type, file!, form.compile),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["models"] });
      setOpen(false);
      setFile(null);
      setForm({ name: "", description: "", hardware_type: "hailo8", compile: true });
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => deleteModel(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["models"] }),
  });

  const showTooltip = (e: React.MouseEvent, text: string) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setTooltip({ x: rect.left + rect.width, y: rect.top, text });
    setTimeout(() => setTooltip(null), 2500);
  };

  const PoCNotice = () => (
    <div className="flex items-start gap-3 p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/50 rounded-xl">
      <Info size={16} className="text-amber-500 flex-shrink-0 mt-0.5" />
      <div>
        <p className="text-sm font-semibold text-amber-800 dark:text-amber-400">Not Available in this PoC</p>
        <p className="text-xs text-amber-700 dark:text-amber-500 mt-0.5">
          Switch to Demo Mode to explore training and dataset management with mock data.
        </p>
      </div>
    </div>
  );

  return (
    <div className="w-full max-w-[1600px] mx-auto space-y-8 animate-fade-in px-4 sm:px-6 lg:px-12 py-8">

      {tooltip && (
        <div
          className="fixed z-[100] bg-gray-900 text-white text-xs px-3 py-2 rounded-lg shadow-xl"
          style={{ top: `${tooltip.y}px`, left: `${tooltip.x + 10}px` }}
        >
          {tooltip.text}
          <div className="absolute left-[-6px] top-2 w-3 h-3 bg-gray-900 rotate-45" />
        </div>
      )}

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl md:text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-emerald-500 mb-2">
            Models & Training
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Manage AI models and training datasets.
          </p>
        </div>
        <Button onClick={() => setOpen(true)} className="gap-2 shrink-0">
          <Plus size={16} /> Upload model
        </Button>
      </div>

      {/* Model list */}
      <div className="grid gap-4">
        {isLoading && !isDemo ? (
          <div className="text-center py-10 text-gray-500">Loading models...</div>
        ) : models.length === 0 ? (
          <Card className="border-dashed border-2 bg-transparent shadow-none opacity-60">
            <div className="flex items-center justify-between p-4">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center border border-gray-200 dark:border-gray-700">
                  <Brain size={20} className="text-gray-400" />
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-base font-bold text-gray-500 dark:text-gray-400">Empty Model Slot</span>
                    <Badge variant="muted">N/A</Badge>
                  </div>
                  <p className="text-xs text-gray-400">No models uploaded yet</p>
                </div>
              </div>
              <Button variant="outline" size="sm" className="gap-2 shrink-0" onClick={() => setOpen(true)}>
                <Upload size={14} /> Upload First Model
              </Button>
            </div>
          </Card>
        ) : (
          models.map((m: any) => {
            const cfg = STATUS_CONFIG[m.compile_status as keyof typeof STATUS_CONFIG] || STATUS_CONFIG.pending;
            const StatusIcon = cfg.icon;
            return (
              <Card key={m.id} className="group hover:border-pink-500 transition-colors">
                <div className="flex items-center justify-between p-4">
                  <div className="flex items-start gap-4">
                    <div className="w-10 h-10 rounded-xl bg-gray-50 dark:bg-gray-800 flex items-center justify-center border border-gray-100 dark:border-gray-700">
                      <StatusIcon size={20} className={cfg.color} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-base font-bold text-gray-900 dark:text-white">{m.name}</span>
                        <Badge variant={cfg.badge}>{m.compile_status}</Badge>
                      </div>
                      <p className="text-xs text-gray-500">
                        {HW_LABELS[m.hardware_type as keyof typeof HW_LABELS] || m.hardware_type || "—"}
                      </p>
                      {m.compile_error && (
                        <p className="text-xs text-red-500 mt-1 font-mono">{m.compile_error.slice(0, 80)}</p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost" size="sm" className="gap-2 shrink-0"
                      onClick={e => showTooltip(e, "Not Available in this PoC")}
                    >
                      <RotateCcw size={14} /> Retrain
                    </Button>
                    <button
                      onClick={() => remove.mutate(m.id)}
                      className="p-2 text-gray-400 hover:text-red-500 transition-colors"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              </Card>
            );
          })
        )}
      </div>

      {/* Training + Dataset section */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-8 border-t border-gray-200 dark:border-gray-800">

        <Card className="border-pink-200 dark:border-pink-900/30 p-6">
          <CardTitle className="mb-4 flex items-center gap-2">
            <Brain className="text-pink-500" size={20} /> New Training Job
          </CardTitle>
          {!isDemo ? (
            <PoCNotice />
          ) : (
            <div className="space-y-4">
              <Select
                label="YOLO Version"
                options={activeVersions.length > 0 ? activeVersions : [{ value: "", label: "No versions available" }]}
                disabled={activeVersions.length === 0}
              />
              <Select
                label="Select Dataset"
                options={
                  activeDatasets.length > 0
                    ? activeDatasets.map((d: string) => ({ value: d, label: d }))
                    : [{ value: "", label: "No datasets available" }]
                }
                disabled={activeDatasets.length === 0}
              />
              <Button
                className="w-full bg-pink-600 hover:bg-pink-700"
                onClick={e => showTooltip(e, "Not Available in this PoC")}
              >
                Start Training
              </Button>
            </div>
          )}
        </Card>

        <Card className="border-emerald-200 dark:border-emerald-900/30 p-6">
          <CardTitle className="mb-4 flex items-center gap-2">
            <Layers className="text-emerald-500" size={20} /> Dataset Management
          </CardTitle>
          {!isDemo ? (
            <PoCNotice />
          ) : (
            <div className="space-y-3">
              {activeDatasets.length === 0 ? (
                <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-dashed border-gray-300 dark:border-gray-700 text-center text-sm text-gray-500 italic">
                  No datasets uploaded yet.
                </div>
              ) : (
                activeDatasets.map((ds: string) => (
                  <div key={ds} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-100 dark:border-gray-700">
                    <span className="text-sm font-medium">{ds}</span>
                    <Button variant="ghost" size="sm" onClick={e => showTooltip(e, "Dataset management not enabled in this PoC")}>
                      Manage
                    </Button>
                  </div>
                ))
              )}
              <Button
                variant="outline" className="w-full mt-2"
                onClick={e => showTooltip(e, "Dataset upload not available in this PoC")}
              >
                <Upload size={16} className="mr-2" /> Upload Dataset
              </Button>
            </div>
          )}
        </Card>

      </section>

      {/* Upload modal */}
      <Modal open={open} onClose={() => { setOpen(false); setFile(null); }} title="Upload Model">
        <form onSubmit={e => { e.preventDefault(); if (file) upload.mutate(); }} className="flex flex-col gap-5 pt-4">
          <Input
            label="Model name"
            value={form.name}
            onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
            placeholder="e.g. yolov8n-door-detector"
            required
          />
          <Input
            label="Description (optional)"
            value={form.description}
            onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
            placeholder="Brief description..."
          />
          <Select
            label="Target hardware"
            value={form.hardware_type}
            onChange={e => setForm(f => ({ ...f, hardware_type: e.target.value }))}
            options={HW_OPTIONS}
          />
          <div
            className="border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-xl p-8 flex flex-col items-center cursor-pointer hover:border-pink-400 transition-colors"
            onClick={() => fileRef.current?.click()}
          >
            <Upload size={28} className="text-gray-400 mb-2" />
            <p className="text-sm text-gray-500">
              {file
                ? <span className="text-pink-500 font-medium">{file.name}</span>
                : "Click to upload .pt file"}
            </p>
            <input
              ref={fileRef} type="file" accept=".pt" className="hidden"
              onChange={e => setFile(e.target.files?.[0] || null)}
            />
          </div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox" checked={form.compile}
              onChange={e => setForm(f => ({ ...f, compile: e.target.checked }))}
              className="w-4 h-4 rounded accent-pink-500"
            />
            <span className="text-sm text-gray-700 dark:text-gray-300">Compile automatically after upload</span>
          </label>
          <Button
            type="submit" className="w-full"
            disabled={!file || upload.isPending}
            loading={upload.isPending}
          >
            Upload Model
          </Button>
        </form>
      </Modal>
    </div>
  );
}
