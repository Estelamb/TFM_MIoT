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
  if (useDataMode.getState().mode === "demo") {
    return ["hailo8", "hailo8l", "aicam", "rpi", "jetson_orin_nano"];
  }
  return api.get<string[]>("/api/devices/hardware-types").then(r => r.data);
};

export const getSensors = async (): Promise<string[]> => {
  if (useDataMode.getState().mode === "demo") {
    return ["rpi_camera_module_3", "dht22_temperature", "ultrasonic_hcsr04", "imu_6dof"];
  }
  return api.get<string[]>("/api/devices/sensors").then(r => r.data);
};

export const getActuators = async (): Promise<string[]> => {
  if (useDataMode.getState().mode === "demo") {
    return ["relay_5v_module", "servo_sg90", "buzzer_alarm", "led_status_rgb"];
  }
  return api.get<string[]>("/api/devices/actuators").then(r => r.data);
};


export interface Device {
  id: string; name: string; hardware_type: HardwareType;
  description?: string; status: "online" | "offline"; last_seen_at?: string; created_at: string;
  sensors?: string[];
  actuators?: string[];
  others?: string[];
}

export const getDevices = async (): Promise<Device[]> => {
  if (useDataMode.getState().mode === "demo") return useDataMode.getState().demoData.devices;
  return api.get<Device[]>("/api/devices").then(r => r.data);
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
}

export const getModels = async (): Promise<Model[]> => {
  if (useDataMode.getState().mode === "demo") return useDataMode.getState().demoData.models;
  return api.get<Model[]>("/api/models").then(r => r.data);
};

export const deleteModel = async (id: string) => {
  if (useDataMode.getState().mode === "demo") {
    const currentModels = useDataMode.getState().demoData.models;
    useDataMode.setState({
      demoData: {
        ...useDataMode.getState().demoData,
        models: currentModels.filter((m: any) => m.id !== id),
      },
    });
    return;
  }
  return api.delete(`/api/models/${id}`);
};

export async function uploadModel(
  name: string, description: string, file: File, dataset_id?: string,
  base_architecture?: string, epochs?: number, input_size?: string,
  batch_size?: number, dataset_version_id?: string
): Promise<Model> {
  if (useDataMode.getState().mode === "demo") {
    const newModel: Model = {
      id: `demo-model-${Date.now()}`,
      name: name,
      description: description,
      compile_status: "ready",
      created_at: new Date().toISOString(),
      dataset_id: dataset_id,
      dataset_version_id: dataset_version_id,
      base_architecture: base_architecture || "yolov8n.pt",
      epochs: epochs,
      input_size: input_size,
      batch_size: batch_size,
    };
    const currentModels = useDataMode.getState().demoData.models;
    useDataMode.setState({
      demoData: {
        ...useDataMode.getState().demoData,
        models: [newModel, ...currentModels],
      },
    });
    return newModel;
  }
  const fd = new FormData();
  fd.append("name", name); fd.append("description", description);
  fd.append("compile", "false");
  if (dataset_id) fd.append("dataset_id", dataset_id);
  if (dataset_version_id) fd.append("dataset_version_id", dataset_version_id);
  if (base_architecture) fd.append("base_architecture", base_architecture);
  if (epochs) fd.append("epochs", epochs.toString());
  if (input_size) fd.append("input_size", input_size);
  if (batch_size) fd.append("batch_size", batch_size.toString());
  fd.append("file", file);
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
  if (useDataMode.getState().mode === "demo") {
    const newModel: Model = {
      id: `demo-model-${Date.now()}`,
      name: body.name,
      description: body.description || "Demo trained model",
      compile_status: "training",
      created_at: new Date().toISOString(),
      dataset_id: body.dataset_id,
      base_architecture: body.base_model || "yolov8n.pt",
      epochs: body.epochs,
      input_size: body.input_size,
      batch_size: 16
    };
    const currentModels = useDataMode.getState().demoData.models;
    useDataMode.setState({
      demoData: {
        ...useDataMode.getState().demoData,
        models: [newModel, ...currentModels]
      }
    });

    // Simulate training completion after 5 seconds
    setTimeout(() => {
      const current = useDataMode.getState().demoData.models;
      const updated = current.map((m: any) =>
        m.id === newModel.id ? { ...m, compile_status: "ready" } : m
      );
      useDataMode.setState({
        demoData: {
          ...useDataMode.getState().demoData,
          models: updated
        }
      });
    }, 5000);

    return newModel;
  }
  return api.post<Model>("/api/models/train", body).then(r => r.data);
};

export const getModelDownloadUrl = async (modelId: string, type: "source" | "compiled"): Promise<{ url: string }> => {
  if (useDataMode.getState().mode === "demo") return { url: "#" };
  return api.get<{ url: string }>(`/api/models/${modelId}/download/${type}`).then(r => r.data);
};

export const getBaseModelOptions = async (): Promise<string[]> => {
  if (useDataMode.getState().mode === "demo") {
    return [
      "yolov10b.pt", "yolov10n.pt", "yolov10s.pt", "yolov10x.pt",
      "yolov11l.pt", "yolov11m.pt", "yolov11n.pt", "yolov11s.pt", "yolov11x.pt",
      "yolov3_416.pt", "yolov3_gluon_416.pt", "yolov3_gluon.pt", "yolov3.pt",
      "yolov4_leaky.pt", "yolov5m_6.1.pt", "yolov5m6_6.1.pt",
      "yolov5m_vehicles_nv12.pt", "yolov5m_vehicles.pt", "yolov5m_vehicles_yuy2.pt",
      "yolov5m_wo_spp.pt", "yolov5m_wo_spp_yuy2.pt", "yolov5m.pt",
      "yolov5s_bbox_decoding_only.pt", "yolov5s_c3tr.pt", "yolov5s_personface_nv12.pt",
      "yolov5s_personface_rgbx.pt", "yolov5s_personface.pt", "yolov5s_wo_spp.pt",
      "yolov5s.pt", "yolov5xs_wo_spp_nms_core.pt", "yolov5xs_wo_spp.pt",
      "yolov6n_0.2.1_nms_core.pt", "yolov6n_0.2.1.pt", "yolov6n.pt",
      "yolov7e6.pt", "yolov7_tiny.pt", "yolov7.pt", "yolov8l.pt",
      "yolov8m.pt", "yolov8n.pt", "yolov8s_bbox_decoding_only.pt",
      "yolov8s.pt", "yolov8x.pt", "yolov9c.pt",
      "yolox_l_leaky.pt", "yolox_s_leaky.pt", "yolox_s_wide_leaky.pt",
      "yolox_tiny.pt"
    ];
  }
  return api.get<string[]>("/api/models/base-model-options").then(r => r.data);
};

export const getBaseModelDownloadUrl = async (filename: string): Promise<{ url: string }> => {
  if (useDataMode.getState().mode === "demo") return { url: "#" };
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
  if (useDataMode.getState().mode === "demo") {
    return useDataMode.getState().demoData.datasets.map((name, i) => ({
      id: `ds-${i}`,
      name,
      description: `Demo dataset ${name}`,
      created_at: new Date().toISOString(),
      object_key: "demo-key",
      sha256: "demo-sha",
      size_bytes: 15420102,
      metadata: { num_classes: 5 },
    }));
  }
  return api.get<Dataset[]>("/api/datasets").then(r => r.data);
};

export const createDataset = async (body: {
  name: string;
  description?: string;
  file?: File;
  version?: string;
  version_description?: string;
}) => {
  if (useDataMode.getState().mode === "demo") {
    const currentDatasets = useDataMode.getState().demoData.datasets;
    useDataMode.setState({
      demoData: {
        ...useDataMode.getState().demoData,
        datasets: [...currentDatasets, body.name],
      },
    });
    return {
      id: `ds-${currentDatasets.length}`,
      name: body.name,
      description: body.description || "Demo dataset",
      created_at: new Date().toISOString(),
    } as Dataset;
  }
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
  if (useDataMode.getState().mode === "demo") {
    return { id: datasetId, name: "Demo", created_at: new Date().toISOString() };
  }
  const fd = new FormData();
  fd.append("file", file);
  if (version) fd.append("version", version);
  if (versionDescription) fd.append("version_description", versionDescription);
  return api.put<Dataset>(`/api/datasets/${datasetId}/file`, fd).then(r => r.data);
};

export const getDatasetDownloadUrl = async (datasetId: string): Promise<{ url: string }> => {
  if (useDataMode.getState().mode === "demo") return { url: "#" };
  return api.get<{ url: string }>(`/api/datasets/${datasetId}/download`).then(r => r.data);
};

export const getDatasetVersionDownloadUrl = async (datasetId: string, versionId: string): Promise<{ url: string }> => {
  if (useDataMode.getState().mode === "demo") return { url: "#" };
  return api.get<{ url: string }>(`/api/datasets/${datasetId}/versions/${versionId}/download`).then(r => r.data);
};

export const deleteDataset = async (id: string) => {
  if (useDataMode.getState().mode === "demo") {
    const currentDatasets = useDataMode.getState().demoData.datasets;
    const match = id.match(/^ds-(\d+)$/);
    if (match) {
      const idx = parseInt(match[1], 10);
      const newDatasets = [...currentDatasets];
      newDatasets.splice(idx, 1);
      useDataMode.setState({
        demoData: {
          ...useDataMode.getState().demoData,
          datasets: newDatasets,
        },
      });
    }
    return;
  }
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
  if (useDataMode.getState().mode === "demo") return useDataMode.getState().demoData.scripts;
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
  if (useDataMode.getState().mode === "demo") {
    return [];  // Demo mode uses hardcoded halDocs
  }
  return api.get<{ libraries: LibraryGroup[] }>("/api/scripts/libraries").then(r => r.data.libraries);
};

// ── Deployments ───────────────────────────────────────────────────────────────
export type DeployStatus = "pending" | "sent" | "running" | "failed";

export interface Deployment {
  id: string; device_id: string; model_id: string; script_id: string;
  status: DeployStatus; sent_at?: string; running_at?: string;
  error_msg?: string; created_at: string; name?: string;
}

export const getDeployments = async (): Promise<Deployment[]> => {
  if (useDataMode.getState().mode === "demo") return useDataMode.getState().demoData.deployments;
  return api.get<Deployment[]>("/api/deployments").then(r => r.data);
};

// Backend expects { device_id, model_id, script_id } (singular device_id)
// The page handles multi-device by calling this once per device
export const createDeployment = (body: { device_ids: string[]; model_id: string; script_id: string; name?: string }) => {
  const device_id = body.device_ids[0];
  return api.post<Deployment>("/api/deployments", {
    device_id,
    model_id: body.model_id,
    script_id: body.script_id,
    name: body.name,
  }).then(r => r.data);
};

export const deleteDeployment = (id: string) => api.delete(`/api/deployments/${id}`);

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
  if (useDataMode.getState().mode === "demo") {
    const currentModels = useDataMode.getState().demoData.models;
    const updated = currentModels.map((m: any) =>
      m.id === id ? { ...m, ...body } : m
    );
    useDataMode.setState({
      demoData: {
        ...useDataMode.getState().demoData,
        models: updated,
      },
    });
    const found = updated.find((m: any) => m.id === id);
    if (!found) throw new Error("Model not found");
    return found;
  }
  return api.put<Model>(`/api/models/${id}`, body).then(r => r.data);
};

export interface UpdateDatasetRequest {
  name: string;
  description?: string;
}

export const updateDataset = async (id: string, body: UpdateDatasetRequest): Promise<Dataset> => {
  if (useDataMode.getState().mode === "demo") {
    const currentDatasets = useDataMode.getState().demoData.datasets;
    const match = id.match(/^ds-(\d+)$/);
    if (match) {
      const idx = parseInt(match[1], 10);
      const newDatasets = [...currentDatasets];
      newDatasets[idx] = body.name;
      useDataMode.setState({
        demoData: {
          ...useDataMode.getState().demoData,
          datasets: newDatasets,
        },
      });
      return {
        id,
        name: body.name,
        description: body.description,
        created_at: new Date().toISOString(),
      };
    }
    throw new Error("Dataset not found");
  }
  return api.put<Dataset>(`/api/datasets/${id}`, body).then(r => r.data);
};

export interface UpdateDeviceRequest {
  name: string;
  description?: string;
}

export const updateDevice = async (id: string, body: UpdateDeviceRequest): Promise<Device> => {
  if (useDataMode.getState().mode === "demo") {
    const currentDevices = useDataMode.getState().demoData.devices;
    const updated = currentDevices.map((d: any) =>
      d.id === id ? { ...d, ...body } : d
    );
    useDataMode.setState({
      demoData: {
        ...useDataMode.getState().demoData,
        devices: updated,
      },
    });
    const found = updated.find((d: any) => d.id === id);
    if (!found) throw new Error("Device not found");
    return found;
  }
  return api.put<Device>(`/api/devices/${id}`, body).then(r => r.data);
};
