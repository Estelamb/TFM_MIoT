import axios from "axios";
import { useDataMode } from "@/hooks/useDataMode";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const api = axios.create({ baseURL: API_URL });

// Auth Interceptor
api.interceptors.request.use((config) => {
  const token = typeof window !== "undefined" ? localStorage.getItem("aura_token") : null;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// ── Auth ──────────────────────────────────────────────────────────────────────
export async function login(username: string, password: string): Promise<string> {
  const form = new URLSearchParams({ username, password });
  const { data } = await api.post("/auth/token", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return data.access_token;
}

// ── Devices ───────────────────────────────────────────────────────────────────
export const HARDWARE_TYPES = ["hailo8", "hailo8l", "rpi_ai_cam", "rpi", "jetson_orin_nano"] as const;
export type HardwareType = typeof HARDWARE_TYPES[number];

export interface Device {
  id: string; name: string; hardware_type: HardwareType;
  description?: string; status: "online" | "offline"; last_seen_at?: string; created_at: string;
}

export const getDevices = async (): Promise<Device[]> => {
  if (useDataMode.getState().mode === "demo") return useDataMode.getState().demoData.devices;
  return api.get<Device[]>("/api/devices").then(r => r.data);
};

export const createDevice = (body: { name: string; hardware_type: string; description?: string }) =>
  api.post<Device>("/api/devices", body).then(r => r.data);

export const deleteDevice = (id: string) => api.delete(`/api/devices/${id}`);

// ── Models ────────────────────────────────────────────────────────────────────
export type CompileStatus = "pending" | "compiling" | "ready" | "failed";

export interface Model {
  id: string; name: string; description?: string; hardware_type?: string;
  compile_status: CompileStatus; compile_error?: string; created_at: string;
}

export const getModels = async (): Promise<Model[]> => {
  if (useDataMode.getState().mode === "demo") return useDataMode.getState().demoData.models;
  return api.get<Model[]>("/api/models").then(r => r.data);
};

export const deleteModel = (id: string) => api.delete(`/api/models/${id}`);

export async function uploadModel(
  name: string, description: string, hardware_type: string, file: File, compile = true
): Promise<Model> {
  const fd = new FormData();
  fd.append("name", name); fd.append("description", description);
  fd.append("hardware_type", hardware_type);
  fd.append("compile", compile ? "true" : "false");
  fd.append("file", file);
  return api.post<Model>("/api/models", fd).then(r => r.data);
}

// ── Scripts ───────────────────────────────────────────────────────────────────
export interface Script {
  id: string; name: string; description?: string;
  hardware_type: string; script_sha256?: string; created_at: string; content?: string;
}

export const getScripts = async (): Promise<Script[]> => {
  if (useDataMode.getState().mode === "demo") return useDataMode.getState().demoData.scripts;
  return api.get<Script[]>("/api/scripts").then(r => r.data);
};

export const deleteScript = (id: string) => api.delete(`/api/scripts/${id}`);

export async function uploadScript(
  name: string, description: string, hardware_type: string, file: File
): Promise<Script> {
  const fd = new FormData();
  fd.append("name", name); fd.append("description", description);
  fd.append("hardware_type", hardware_type); fd.append("file", file);
  return api.post<Script>("/api/scripts", fd).then(r => r.data);
}

// ── Deployments ───────────────────────────────────────────────────────────────
export type DeployStatus = "pending" | "sent" | "running" | "failed";

export interface Deployment {
  id: string; device_id: string; model_id: string; script_id: string;
  status: DeployStatus; sent_at?: string; running_at?: string;
  error_msg?: string; created_at: string;
}

export const getDeployments = async (): Promise<Deployment[]> => {
  if (useDataMode.getState().mode === "demo") return useDataMode.getState().demoData.deployments;
  return api.get<Deployment[]>("/api/deployments").then(r => r.data);
};

// Backend expects { device_id, model_id, script_id } (singular device_id)
// The page handles multi-device by calling this once per device
export const createDeployment = (body: { device_ids: string[]; model_id: string; script_id: string }) => {
  const device_id = body.device_ids[0];
  return api.post<Deployment>("/api/deployments", {
    device_id,
    model_id: body.model_id,
    script_id: body.script_id,
  }).then(r => r.data);
};

// ── Monitoring ────────────────────────────────────────────────────────────────
export interface DeviceState {
  device_id: string; status: string; cpu_percent: number; ram_percent: number;
  ram_used_mb: number; active_model_id: string; active_script_id: string;
  active_deployment_id: string; last_seen_at: string; coordinates?: [number, number];
}

export interface InferenceResult {
  timestamp: string; deployment_id: string; result_json: string;
}

export const getMonitoringStates = async (): Promise<DeviceState[]> => {
  if (useDataMode.getState().mode === "demo") return useDataMode.getState().demoData.monitoringStates;
  return api.get<DeviceState[]>("/api/monitoring/devices").then(r => r.data);
};

export const getDeviceState = (id: string) =>
  api.get<DeviceState>(`/api/monitoring/devices/${id}`).then(r => r.data);

export const getInferenceResults = (device_id: string, limit = 20) =>
  api.get<InferenceResult[]>(`/api/monitoring/devices/${device_id}/inference?limit=${limit}`).then(r => r.data);
