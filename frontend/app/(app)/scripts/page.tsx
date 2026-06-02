"use client";
import { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import { getScripts, deleteScript, uploadScript, HARDWARE_TYPES } from "@/lib/api";
import { useDataMode } from "@/hooks/useDataMode";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Select } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { HW_LABELS } from "@/lib/utils";
import {
  Code2, Plus, Trash2, FileCode, ArrowLeft, Save,
  Loader2, Upload, Download, BookOpen, Info,
} from "lucide-react";

const Editor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => (
    <div className="h-[500px] flex items-center justify-center bg-gray-900 text-white">
      <Loader2 className="animate-spin mr-2" /> Loading Editor...
    </div>
  ),
});

const HW_OPTIONS = HARDWARE_TYPES.map(v => ({ value: v, label: HW_LABELS[v] || v }));

const SCRIPT_TEMPLATE = `"""
AURA Edge Script Template
=========================
Implement pre_inference() and post_inference().
The runtime calls run(raw_input) automatically.
"""
from aura_hw import execute_inference
import numpy as np

INPUT_WIDTH  = 640
INPUT_HEIGHT = 640
CONF_THRESHOLD = 0.5
CLASSES = ["person", "car", "dog"]  # adjust to your labels


def pre_inference(raw_input):
    """Preprocess raw input → numpy tensor ready for the model."""
    import cv2
    img = cv2.resize(raw_input, (INPUT_WIDTH, INPUT_HEIGHT))
    img = img.astype(np.float32) / 255.0
    img = np.transpose(img, (2, 0, 1))   # HWC → CHW
    return np.expand_dims(img, axis=0)   # → NCHW


def post_inference(raw_output):
    """Postprocess model output → list of detection dicts."""
    detections = []
    outputs = list(raw_output.values())[0] if isinstance(raw_output, dict) else raw_output
    if outputs is None or len(outputs) == 0:
        return detections
    for box in outputs[0].T:
        scores = box[4:]
        class_id = int(np.argmax(scores))
        confidence = float(scores[class_id])
        if confidence < CONF_THRESHOLD:
            continue
        cx, cy, w, h = box[:4]
        detections.append({
            "class": CLASSES[class_id] if class_id < len(CLASSES) else str(class_id),
            "confidence": round(confidence, 3),
            "bbox": [float(cx), float(cy), float(w), float(h)],
        })
    return detections


# ── DO NOT MODIFY ─────────────────────────────────────────────────────────────
def run(raw_input):
    return post_inference(execute_inference(pre_inference(raw_input)))
`;

export default function ScriptsPage() {
  const { mode, demoData } = useDataMode();
  const isDemo = mode === "demo";
  const qc = useQueryClient();

  const { data: realScripts = [], isLoading } = useQuery({ queryKey: ["scripts"], queryFn: getScripts });
  const scripts = isDemo ? demoData.scripts : realScripts;

  const [editingScript, setEditingScript] = useState<any | null>(null);
  const [code, setCode] = useState("");
  const [lang, setLang] = useState("python");
  const [refLang, setRefLang] = useState("python");

  // Upload modal state (real mode only)
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadForm, setUploadForm] = useState({ name: "", description: "", hardware_type: "hailo8" });
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const uploadFileRef = useRef<HTMLInputElement>(null);

  const editorFileRef = useRef<HTMLInputElement>(null);

  const remove = useMutation({
    mutationFn: (id: string) => deleteScript(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["scripts"] }),
  });

  const uploadMutation = useMutation({
    mutationFn: () =>
      uploadScript(uploadForm.name, uploadForm.description, uploadForm.hardware_type, uploadFile!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["scripts"] });
      setUploadOpen(false);
      setUploadFile(null);
      setUploadForm({ name: "", description: "", hardware_type: "hailo8" });
    },
  });

  // Save from editor: download as file (PoC — no direct update API endpoint)
  const saveFromEditor = () => {
    const ext = lang === "python" ? "py" : lang === "java" ? "java" : "cpp";
    const blob = new Blob([code], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${editingScript?.name?.replace(/\.[^.]+$/, "") || "script"}.${ext}`;
    a.click();
  };

  const handleEditorFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = ev => setCode(ev.target?.result as string);
      reader.readAsText(file);
    }
  };

  const openNewScript = () => {
    if (isDemo) {
      setEditingScript({ name: "New Script" });
      setCode(SCRIPT_TEMPLATE);
    } else {
      setUploadOpen(true);
    }
  };

  // EDITOR VIEW
  if (editingScript) {
    const activeDocs = demoData.halDocs[lang] || [];
    return (
      <div className="h-[calc(100vh-80px)] flex flex-col animate-fade-in">
        <div className="flex items-center justify-between px-6 py-4 border-b dark:border-gray-800 bg-white/50 dark:bg-gray-950/50 backdrop-blur-md">
          <div className="flex items-center gap-4">
            <Button variant="ghost" onClick={() => setEditingScript(null)}><ArrowLeft size={18} /></Button>
            <h2 className="text-lg font-bold">{editingScript.name}</h2>
            <div className="w-40">
              <Select value={lang} onChange={e => setLang(e.target.value)}
                options={[{ value: "python", label: "Python" }, { value: "cpp", label: "C++" }, { value: "java", label: "Java" }]} />
            </div>
          </div>
          <div className="flex gap-2 items-center">
            {!isDemo && (
              <div className="flex items-center gap-1.5 text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 px-3 py-1.5 rounded-lg border border-amber-200 dark:border-amber-800/50">
                <Info size={12} /> Save downloads the file — upload via Scripts page
              </div>
            )}
            <input type="file" ref={editorFileRef} className="hidden" accept=".py,.cpp,.java" onChange={handleEditorFileUpload} />
            <Button variant="outline" size="sm" onClick={() => editorFileRef.current?.click()}>
              <Upload size={14} className="mr-2" /> Upload
            </Button>
            <Button variant="outline" size="sm" onClick={saveFromEditor}>
              <Download size={14} className="mr-2" /> Download
            </Button>
            <Button size="sm" onClick={saveFromEditor}>
              <Save size={14} className="mr-2" /> Save
            </Button>
          </div>
        </div>

        <div className="flex flex-1 overflow-hidden">
          <div className="flex-1 border-r dark:border-gray-800">
            <Editor height="100%" language={lang} theme="vs-dark" value={code} onChange={v => setCode(v || "")} />
          </div>
          {activeDocs.length > 0 && (
            <div className="w-80 bg-gray-50 dark:bg-gray-950 p-6 overflow-y-auto">
              <div className="flex items-center gap-2 mb-6 text-orange-500 font-bold">
                <BookOpen size={20} /> HAL API: {lang.toUpperCase()}
              </div>
              <div className="space-y-6">
                {activeDocs.map((fn: any, i: number) => (
                  <div key={i} className="space-y-1">
                    <code className="text-sm font-mono text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 px-2 py-1 rounded">
                      {fn.name}
                    </code>
                    <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">{fn.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // MAIN VIEW
  const mainViewDocs = demoData.halDocs[refLang] || [];

  return (
    <div className="w-full max-w-[1600px] mx-auto space-y-8 animate-fade-in px-4 sm:px-6 lg:px-12 py-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl md:text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-orange-500 mb-2">
            Scripts
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Manage inference logic and HAL integration scripts.
          </p>
        </div>
        <Button onClick={openNewScript} className="gap-2 shrink-0">
          <Plus size={16} /> {isDemo ? "New Script" : "Upload Script"}
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Scripts list */}
        <div className="lg:col-span-2 space-y-4">
          {isLoading && !isDemo ? (
            <div className="text-center py-10 text-gray-500">Loading scripts...</div>
          ) : scripts.length === 0 ? (
            <Card className="border-dashed border-2 bg-transparent shadow-none opacity-60">
              <div className="flex items-center justify-between p-4">
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 rounded-xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center border border-gray-200 dark:border-gray-700">
                    <FileCode size={20} className="text-gray-400" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-base font-bold text-gray-500 dark:text-gray-400">Empty Script Slot</span>
                      <Badge variant="muted">N/A</Badge>
                    </div>
                    <p className="text-xs text-gray-400">No logic defined</p>
                  </div>
                </div>
                <Button variant="outline" size="sm" className="gap-2" onClick={openNewScript}>
                  <Plus size={14} /> {isDemo ? "Create First Script" : "Upload Script"}
                </Button>
              </div>
            </Card>
          ) : (
            scripts.map((s: any) => (
              <Card key={s.id} className="flex justify-between items-center p-5 hover:border-orange-400 transition-all">
                <div className="flex items-center gap-4">
                  <FileCode className="text-orange-500" />
                  <div>
                    <p className="font-bold">{s.name}</p>
                    <p className="text-xs text-gray-500">{HW_LABELS[s.hardware_type] || s.hardware_type}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost" size="sm"
                    onClick={() => { setEditingScript(s); setCode(s.content || SCRIPT_TEMPLATE); }}
                  >
                    Edit
                  </Button>
                  <button
                    onClick={() => remove.mutate(s.id)}
                    className="p-2 text-gray-400 hover:text-red-500 transition-colors"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </Card>
            ))
          )}
        </div>

        {/* HAL Documentation */}
        <div className="lg:col-span-1">
          <Card className="p-6 sticky top-8 border-t-4 border-t-orange-500">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold flex items-center gap-2 text-gray-900 dark:text-white">
                <BookOpen size={18} className="text-orange-500" /> HAL API
              </h2>
            </div>
            <div className="mb-6">
              <Select
                label="Language Reference"
                value={refLang}
                onChange={e => setRefLang(e.target.value)}
                options={[{ value: "python", label: "Python" }, { value: "cpp", label: "C++" }, { value: "java", label: "Java" }]}
              />
            </div>
            <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-2">
              {mainViewDocs.length === 0 ? (
                <p className="text-sm text-gray-500 italic">
                  {isDemo
                    ? "No documentation available for this language."
                    : "HAL documentation not available in Real Mode yet. Switch to Demo Mode to preview."}
                </p>
              ) : (
                mainViewDocs.map((fn: any, i: number) => (
                  <div key={i} className="space-y-1 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-100 dark:border-gray-800">
                    <code className="text-xs font-mono text-blue-600 dark:text-blue-400">{fn.name}</code>
                    <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed mt-1">{fn.desc}</p>
                  </div>
                ))
              )}
            </div>
          </Card>
        </div>
      </div>

      {/* Upload modal (real mode) */}
      <Modal open={uploadOpen} onClose={() => { setUploadOpen(false); setUploadFile(null); }} title="Upload Script">
        <form onSubmit={e => { e.preventDefault(); if (uploadFile) uploadMutation.mutate(); }} className="flex flex-col gap-5 pt-4">
          <Input
            label="Script name"
            value={uploadForm.name}
            onChange={e => setUploadForm(f => ({ ...f, name: e.target.value }))}
            placeholder="e.g. yolov8-hailo-postprocess"
            required
          />
          <Input
            label="Description (optional)"
            value={uploadForm.description}
            onChange={e => setUploadForm(f => ({ ...f, description: e.target.value }))}
            placeholder="Brief description..."
          />
          <Select
            label="Target hardware"
            value={uploadForm.hardware_type}
            onChange={e => setUploadForm(f => ({ ...f, hardware_type: e.target.value }))}
            options={HW_OPTIONS}
          />
          <div
            className="border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-xl p-8 flex flex-col items-center cursor-pointer hover:border-orange-400 transition-colors"
            onClick={() => uploadFileRef.current?.click()}
          >
            <Upload size={28} className="text-gray-400 mb-2" />
            <p className="text-sm text-gray-500">
              {uploadFile ? <span className="text-orange-500 font-medium">{uploadFile.name}</span> : "Click to upload .py file"}
            </p>
            <input ref={uploadFileRef} type="file" accept=".py" className="hidden" onChange={e => setUploadFile(e.target.files?.[0] || null)} />
          </div>
          <Button type="submit" className="w-full" disabled={!uploadFile || uploadMutation.isPending} loading={uploadMutation.isPending}>
            Upload Script
          </Button>
        </form>
      </Modal>
    </div>
  );
}
