import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const api = axios.create({ baseURL: API_URL });

// Auth Interceptor
api.interceptors.request.use((config) => {
  const token = typeof window !== "undefined" ? localStorage.getItem("aura_token") : null;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Response Interceptor to redirect on 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== "undefined") {
        localStorage.removeItem("aura_token");
        document.cookie = "aura_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT;";
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

// ── Auth ──────────────────────────────────────────────────────────────────────
export async function login(username: string, password: string): Promise<string> {
  const form = new URLSearchParams({ username, password });
  const { data } = await api.post("/auth/token", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return data.access_token;
}

// ── Devices ───────────────────────────────────────────────────────────────────
export type HardwareType = string;

export const getHardwareTypes = async (): Promise<string[]> => {
  return api.get<string[]>("/api/devices/hardware-types").then(r => r.data);
};

export const getSensors = async (): Promise<string[]> => {
  return api.get<string[]>("/api/devices/sensors").then(r => r.data);
};

export const getActuators = async (): Promise<string[]> => {
  return api.get<string[]>("/api/devices/actuators").then(r => r.data);
};

export const getOthers = async (): Promise<string[]> => {
  return api.get<string[]>("/api/devices/others").then(r => r.data);
};

export const getPeripheralLabels = async (): Promise<Record<string, string>> => {
  return api.get<Record<string, string>>("/api/devices/labels").then(r => r.data);
};

export interface Device {
  id: string; name: string; hardware_type: HardwareType;
  description?: string; status: "online" | "offline"; last_seen_at?: string; created_at: string;
  sensors?: string[];
  actuators?: string[];
  others?: string[];
}

export const getDevices = async (): Promise<Device[]> => {
  return api.get<Device[]>("/api/devices").then(r => r.data);
};

export const getDevice = async (id: string): Promise<Device> => {
  return api.get<Device>(`/api/devices/${id}`).then(r => r.data);
};

export const createDevice = (body: {
  name: string;
  hardware_type: string;
  description?: string;
  sensors: string[];
  actuators: string[];
  others?: string[];
}) =>
  api.post<Device>("/api/devices", body).then(r => r.data);

export const deleteDevice = (id: string) => api.delete(`/api/devices/${id}`);

// ── Models ────────────────────────────────────────────────────────────────────
export type CompileStatus = "pending" | "compiling" | "ready" | "failed" | "training";

export interface ModelCompilation {
  id: string;
  model_id: string;
  hardware_type: string;
  compiled_key: string;
  compiled_sha256: string;
  compile_status: CompileStatus;
  compile_error?: string;
  created_at: string;
}

export interface Model {
  id: string; name: string; description?: string; hardware_type?: string;
  compile_status: CompileStatus; compile_error?: string; created_at: string;
  dataset_id?: string;
  dataset_version_id?: string;
  base_architecture?: string;
  epochs?: number;
  input_size?: string;
  batch_size?: number;
  source_key?: string;
  compilations?: ModelCompilation[];
}

export const getModels = async (): Promise<Model[]> => {
  return api.get<Model[]>("/api/models").then(r => r.data);
};

export const deleteModel = async (id: string) => {
  return api.delete(`/api/models/${id}`);
};

export async function uploadModel(
  name: string, description: string, file: File, dataset_id?: string,
  base_architecture?: string, epochs?: number, input_size?: string,
  batch_size?: number, dataset_version_id?: string
): Promise<Model> {
  const fd = new FormData();
  fd.append("name", name); fd.append("description", description);
  fd.append("file", file);
  if (dataset_id) fd.append("dataset_id", dataset_id);
  if (dataset_version_id) fd.append("dataset_version_id", dataset_version_id);
  if (base_architecture) fd.append("base_architecture", base_architecture);
  if (epochs) fd.append("epochs", epochs.toString());
  if (input_size) fd.append("input_size", input_size);
  if (batch_size) fd.append("batch_size", batch_size.toString());
  return api.post<Model>("/api/models", fd).then(r => r.data);
}

export interface TrainModelRequest {
  name: string;
  description?: string;
  dataset_id: string;
  dataset_version_id?: string;
  base_model?: string;
  epochs?: number;
  input_size?: string;
  gpu_percent?: number;
  device?: string;
}

export const trainModel = async (body: TrainModelRequest): Promise<Model> => {
  return api.post<Model>("/api/models/train", body).then(r => r.data);
};

export const getModelDownloadUrl = async (modelId: string, type: "source" | "compiled"): Promise<{ url: string }> => {
  return api.get<{ url: string }>(`/api/models/${modelId}/download/${type}`).then(r => r.data);
};

export const getBaseModelOptions = async (): Promise<string[]> => {
  return api.get<string[]>("/api/models/base-model-options").then(r => r.data);
};

export const getBaseModelDownloadUrl = async (filename: string): Promise<{ url: string }> => {
  return api.get<{ url: string }>(`/api/models/base-models/${filename}/download`).then(r => r.data);
};

// ── Datasets ──────────────────────────────────────────────────────────────────
export interface DatasetVersion {
  id: string;
  dataset_id: string;
  version: string;
  description?: string;
  object_key: string;
  sha256: string;
  size_bytes: number;
  metadata?: { num_classes?: number; [key: string]: any } | null;
  created_at: string;
}

export interface Dataset {
  id: string;
  name: string;
  description?: string;
  created_at: string;
  object_key?: string | null;
  sha256?: string | null;
  size_bytes?: number | null;
  metadata?: { num_classes?: number; [key: string]: any } | null;
  versions?: DatasetVersion[];
}

export const getDatasets = async (): Promise<Dataset[]> => {
  return api.get<Dataset[]>("/api/datasets").then(r => r.data);
};

export const createDataset = async (body: {
  name: string;
  description?: string;
  file?: File;
  version?: string;
  version_description?: string;
}) => {
  const fd = new FormData();
  fd.append("name", body.name);
  if (body.description) fd.append("description", body.description);
  if (body.file) fd.append("file", body.file);
  if (body.version) fd.append("version", body.version);
  if (body.version_description) fd.append("version_description", body.version_description);
  return api.post<Dataset>("/api/datasets", fd).then(r => r.data);
};

export const replaceDatasetFile = async (
  datasetId: string,
  file: File,
  version?: string,
  versionDescription?: string
): Promise<Dataset> => {
  const fd = new FormData();
  fd.append("file", file);
  if (version) fd.append("version", version);
  if (versionDescription) fd.append("version_description", versionDescription);
  return api.put<Dataset>(`/api/datasets/${datasetId}/file`, fd).then(r => r.data);
};

export const getDatasetDownloadUrl = async (datasetId: string): Promise<{ url: string }> => {
  return api.get<{ url: string }>(`/api/datasets/${datasetId}/download`).then(r => r.data);
};

export const getDatasetVersionDownloadUrl = async (datasetId: string, versionId: string): Promise<{ url: string }> => {
  return api.get<{ url: string }>(`/api/datasets/${datasetId}/versions/${versionId}/download`).then(r => r.data);
};

export const deleteDataset = async (id: string) => {
  return api.delete(`/api/datasets/${id}`);
};

export const associateModelDataset = (modelId: string, datasetId: string, datasetVersionId?: string) => {
  let url = `/api/models/${modelId}/dataset/${datasetId}`;
  if (datasetVersionId) {
    url += `?dataset_version_id=${datasetVersionId}`;
  }
  return api.post<Model>(url).then(r => r.data);
};

// ── Scripts ───────────────────────────────────────────────────────────────────
export interface Script {
  id: string; name: string; description?: string;
  language: string;
  script_sha256?: string; created_at: string; content?: string;
}

export const getScripts = async (): Promise<Script[]> => {
  return api.get<Script[]>("/api/scripts").then(r => r.data);
};

export const deleteScript = (id: string) => api.delete(`/api/scripts/${id}`);

export async function uploadScript(
  name: string, description: string, file: File, language: string
): Promise<Script> {
  const fd = new FormData();
  fd.append("name", name); fd.append("description", description);
  fd.append("file", file);
  fd.append("language", language);
  return api.post<Script>("/api/scripts", fd).then(r => r.data);
}

export interface LibraryEntry {
  name: string;
  desc: string;
  type: "method" | "function";
}

export interface LibraryGroup {
  category: string;
  subcategory: string;
  import_path: string;
  api: LibraryEntry[];
}

export const getLibraries = async (): Promise<LibraryGroup[]> => {
  return api.get<{ libraries: LibraryGroup[] }>("/api/scripts/libraries").then(r => r.data.libraries);
};

// ── Deployments ───────────────────────────────────────────────────────────────
export type DeployStatus = "pending" | "compiling" | "sent" | "running" | "failed" | "stopped";

export interface Deployment {
  id: string; device_id: string; model_id: string; script_id: string;
  status: DeployStatus; sent_at?: string; running_at?: string;
  error_msg?: string; created_at: string; name?: string;
}

export const getDeployments = async (): Promise<Deployment[]> => {
  return api.get<Deployment[]>("/api/deployments").then(r => r.data);
};

export const createDeployment = async (body: { device_ids: string[]; model_id: string; script_id: string; name?: string }): Promise<Deployment> => {
  const device_id = body.device_ids[0];
  return api.post<Deployment>("/api/deployments", {
    device_id,
    model_id: body.model_id,
    script_id: body.script_id,
    name: body.name,
  }).then(r => r.data);
};

export const deleteDeployment = async (id: string): Promise<any> => {
  return api.delete(`/api/deployments/${id}`);
};

// ── Monitoring ────────────────────────────────────────────────────────────────
export interface DeviceState {
  device_id: string; status: string; cpu_percent: number; ram_percent: number;
  ram_used_mb: number; latency_ms: number; active_model_id: string; active_script_id: string;
  active_deployment_id: string; last_seen_at: string; coordinates?: [number, number];
}

export interface InferenceResult {
  timestamp: string; deployment_id: string; result_json: string;
}

export const getMonitoringStates = async (): Promise<DeviceState[]> => {
  return api.get<DeviceState[]>("/api/monitoring/devices").then(r => r.data);
};

export const getDeviceState = async (id: string): Promise<DeviceState> => {
  return api.get<DeviceState>(`/api/monitoring/devices/${id}`).then(r => r.data);
};

export const getInferenceResults = async (device_id: string, limit = 20): Promise<InferenceResult[]> => {
  return api.get<InferenceResult[]>(`/api/monitoring/devices/${device_id}/inference?limit=${limit}`).then(r => r.data);
};

// ── Metadata Management (PUT) ──────────────────────────────────────────────────
export interface UpdateModelRequest {
  name: string;
  description?: string;
  epochs?: number;
  input_size?: string;
  batch_size?: number;
  base_architecture?: string;
}

export const updateModel = async (id: string, body: UpdateModelRequest): Promise<Model> => {
  return api.put<Model>(`/api/models/${id}`, body).then(r => r.data);
};

export interface UpdateDatasetRequest {
  name: string;
  description?: string;
}

export const updateDataset = async (id: string, body: UpdateDatasetRequest): Promise<Dataset> => {
  return api.put<Dataset>(`/api/datasets/${id}`, body).then(r => r.data);
};

export interface UpdateDeviceRequest {
  name: string;
  description?: string;
}

export const updateDevice = async (id: string, body: UpdateDeviceRequest): Promise<Device> => {
  return api.put<Device>(`/api/devices/${id}`, body).then(r => r.data);
};
