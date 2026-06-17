# AURA Platform

Edge AI deployment platform for IoT devices. Upload a trained YOLOv8 model, compile it for your target hardware, and deploy it to remote edge devices over MQTT — all from a single dashboard.

---

## What it does

1. **Register** edge devices (Hailo-8, Hailo-8L, RPi AI Camera, Jetson Orin Nano, plain RPi)
2. **Upload** a trained `.pt` model and the platform compiles it to the right format for the target hardware
3. **Upload** an inference script (pre/post-processing logic)
4. **Deploy** model + script to a device with one click
5. **Monitor** live CPU/RAM telemetry and inference results from all devices

---

## Services

| Service | Port | Stack | Responsibility |
|---|---|---|---|
| `api-gateway` | 8000 (HTTP) | FastAPI + JWT | Single entry point for the frontend. Proxies to gRPC services. |
| `registry-service` | 50051 (gRPC) | Python + PostgreSQL + MinIO | Metadata registry for devices, datasets, models, and scripts. |
| `mlops-service` | 50052 (gRPC) | Python + Docker socket | Handles model training and compilation asynchronously. |
| `edge-connector-service` | 50053 (gRPC) + 9100 (Prometheus) | Python + PostgreSQL + MQTT + MongoDB | Telemetry ingest, inference logging, and OTA deployment. |
| `frontend` | 3000 (HTTP) | Next.js 15 + Tailwind | Dashboard UI. |

---

## Repository structure

```
aura/
├── docker-compose.yml              # Full stack
├── docker/                         # Per-service debug composes
│   ├── api-gateway.yml
│   ├── frontend.yml
│   └── mlops-service.yml
│
├── infra/
│   ├── mosquitto/mosquitto.conf    # MQTT broker config (anonymous, port 1883)
│   └── postgres/init.sql           # DB schema (devices, models, scripts, deployments)
│
├── shared/
│   ├── proto/                      # Protobuf definitions (source of truth for all APIs)
│   ├── proto_gen/                  # Generated gRPC stubs — do not edit manually
│   ├── transport/                  # Pluggable transport layer (MQTT implemented)
│   └── utils/                      # Shared: database, MinIO, logging, gRPC server helper
│
├── services/
│   ├── api-gateway/                # API Gateway microservice (FastAPI REST to gRPC)
│   ├── registry-service/           # Devices, models, and scripts metadata registry
│   ├── mlops-service/              # Model compilation orchestrator
│   └── edge-connector-service/     # Telemetry ingest and OTA deployment broker
│
├── edge-runtime/
│   ├── agent.py                    # Edge agent: subscribes to MQTT commands
│   ├── aura_hw/                    # Hardware abstraction library
│   │   ├── detect.py               # Auto-detects hardware type
│   │   ├── runtime.py              # Public API: load_model(), execute_inference()
│   │   └── backends/               # Hardware target backends
│   │       ├── devices/            # Hardware-specific devices (actuators, cameras, sensors)
│   │       └── inference/          # Inference processing engine backends
│   └── pal/                        # Platform Abstraction Layer (communication client)
│
├── docs/                           # Documentation folder (Sphinx & TypeDoc)
│   ├── sphinx/                     # Sphinx python documentation source and configs
│   └── typedoc/                    # TypeDoc configuration for TS frontend
│
└── frontend/
    ├── app/                        # Next.js App Router
    │   ├── (auth)/login/           # Login page
    │   └── (app)/                  # Authenticated layout + all pages
    │       ├── dashboard/          # Overview + live telemetry
    │       ├── devices/            # Device management
    │       ├── models/             # Model upload + compilation status
    │       ├── scripts/            # Script upload
    │       ├── deployments/        # Create and track deployments
    │       └── monitoring/         # Per-device telemetry + inference results
    ├── components/                 # React components
    ├── hooks/                      # Custom React hooks (WS sub, query etc.)
    └── lib/                        # Axios clients & layout helpers
```

---

## Database schema

PostgreSQL manages the core entities. MongoDB stores time-series telemetry and inference results.

**PostgreSQL tables:**

```
devices       — registered edge devices (id, name, hardware_type, status)
models        — uploaded .pt files + compilation state (source_key, compiled_key, compile_status)
scripts       — inference scripts (script_key, script_sha256, hardware_type)
deployments   — links device + model + script (status: pending → sent → running | failed)
```

**MongoDB collections (edge-connector-service):**

```
device_states      — current state per device (upsert on each telemetry message)
inference_results  — append-only inference outputs with timestamp
```

**MinIO buckets:**

```
models     — original .pt files
compiled   — compiled model artifacts (.hef, packerOut.zip, .tflite)
scripts    — inference scripts (.py)
```

---

## Deployment flow

```
1. User uploads .pt model
   └─▶ api-gateway saves to MinIO (models bucket)
   └─▶ registry-service registers model in PostgreSQL (compile_status = pending)
   └─▶ mlops-service.CompileModel() called [non-blocking, returns immediately]
       └─▶ background task: export ONNX → Hailo Docker / MCT Python pipeline
       └─▶ uploads compiled artifact to MinIO (compiled bucket)
       └─▶ notifies registry-service: UpdateModelCompiled (compile_status = ready)

2. User creates deployment (device + model + script)
   └─▶ edge-connector-service generates presigned MinIO URLs (1h TTL)
   └─▶ publishes to MQTT: device/{id}/commands
       { "command": "deploy", "model_url", "model_sha256", "script_url", "script_sha256" }
   └─▶ marks deployment status = sent

3. Edge agent receives command
   └─▶ downloads model via presigned URL, verifies SHA-256
   └─▶ downloads script, verifies SHA-256
   └─▶ calls aura_hw.load_model() → hardware-specific backend
   └─▶ publishes: device/{id}/events { "event": "deploy_ack" }
   └─▶ edge-connector-service listener updates status = running

4. Edge agent runs continuously
   └─▶ publishes telemetry every N seconds: device/{id}/telemetry
   └─▶ publishes inference results: device/{id}/inference
   └─▶ edge-connector-service stores both in MongoDB + updates Prometheus gauges
```

---

## MQTT topics

| Topic | Direction | Payload |
|---|---|---|
| `device/{id}/commands` | Cloud → Edge | `{ "command": "deploy", "deployment_id", "model_url", "model_sha256", "script_url", "script_sha256" }` |
| `device/{id}/events` | Edge → Cloud | `{ "event": "deploy_ack" \| "deploy_failed", "deployment_id", "error"? }` |
| `device/{id}/telemetry` | Edge → Cloud | `{ "cpu_percent", "ram_percent", "ram_used_mb", "active_model_id", "active_script_id", "active_deployment_id" }` |
| `device/{id}/inference` | Edge → Cloud | `{ "deployment_id", "result_json" }` |

---

## MLOps service

The MLOps service contains a pluggable registry of compilers:

```python
COMPILER_REGISTRY = {
    "hailo8":     HailoCompiler,    # launches hailo_ai_sw_suite Docker container
    "hailo8l":    HailoCompiler,    # same, different --hw-arch flag
    "rpi_ai_cam": AICamCompiler,    # MCT + imx500-converter Python pipeline
    # "rpi":      TFLiteCompiler,   # TODO
    # "jetson_orin_nano": TRTCompiler  # TODO
}
```

**Hailo pipeline** (`compilers/hailo.py`): download `.pt` → export ONNX (`nms=False`, `opset=11`, `batch=1`) → generate calibration images → launch `hailo_ai_sw_suite` Docker container → run `hailomz compile` → upload `.hef` to MinIO.

**AI Camera pipeline** (`compilers/aicam.py`): download `.pt` → generate calibration images → `model.export(format="imx")` via Ultralytics (MCT + imx500-converter) → upload `packerOut.zip` to MinIO.

`CompileModel` RPC returns immediately with `status=compiling`. Compilation runs as a background `asyncio.create_task()` and notifies `registry-service` on completion via `UpdateModelCompiled`.

---

## Hardware abstraction layer (aura_hw)

The inference script only needs to call `execute_inference()`. Hardware detection and routing happen automatically.

```python
from aura_hw import execute_inference

def pre_inference(raw_input):
    # preprocess → numpy tensor
    return tensor

def post_inference(raw_output):
    # postprocess → list of dicts
    return [{"class": "person", "confidence": 0.92, "bbox": [...]}]

def run(raw_input):          # called by the edge runtime
    return post_inference(execute_inference(pre_inference(raw_input)))
```

Hardware detection order: `AURA_HARDWARE_TYPE` env var → `hailortcli` → `/etc/nv_tegra_release` → `libcamera-hello` (IMX500) → `/proc/device-tree/model` (RPi) → TFLite fallback.

---

## Supported hardware

| Device | Model format | Backend | Status |
|---|---|---|---|
| RPi5 + Hailo-8 | `.hef` | HailoRT SDK | ✅ Full |
| RPi5 + Hailo-8L | `.hef` | HailoRT SDK | ✅ Full |
| RPi5 + AI Camera (IMX500) | `packerOut.zip` | picamera2 | ✅ Full |
| RPi5 (CPU only) | `.tflite` | TFLite Runtime | ⚠️ Backend ready, compiler stub |
| Jetson Orin Nano | `.engine` | TensorRT | ⚠️ Stub |

---

## Frontend

Built with Next.js 15 App Router, Tailwind CSS and TanStack Query. Auth via JWT stored in `localStorage`. Dark theme with `aura-*` Tailwind color tokens (`#0a0c10` background, `#6366f1` indigo accent). Live data refetches every 5–10 seconds.

Pages: **Dashboard** · **Devices** · **Models** · **Scripts** · **Deployments** · **Monitoring**

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | — | JWT signing secret. **Change before any deployment.** |
| `POSTGRES_PASSWORD` | `aura_dev` | PostgreSQL password |
| `MINIO_ROOT_PASSWORD` | `aura_dev` | MinIO root password |
| `POSTGRES_USER` | `aura` | PostgreSQL user |
| `POSTGRES_DB` | `aura` | PostgreSQL database name |
| `MINIO_ROOT_USER` | `aura` | MinIO root user |
| `MINIO_BUCKET_MODELS` | `models` | Bucket for source .pt files |
| `MINIO_BUCKET_COMPILED` | `compiled` | Bucket for compiled artifacts |
| `MINIO_BUCKET_SCRIPTS` | `scripts` | Bucket for inference scripts |
| `MQTT_HOST` | `mosquitto` | MQTT broker hostname |
| `MQTT_PORT` | `1883` | MQTT broker port |
| `HAILO_DOCKER_IMAGE` | `hailo_ai_sw_suite:latest` | Docker image for Hailo compilation |
| `LOG_LEVEL` | `INFO` | Log level: DEBUG \| INFO \| WARNING \| ERROR |

---

## Known limitations (PoC)

- Auth uses a hardcoded user (`admin` / `aura2026`). Replace with DB-backed auth in the next iteration.
- Calibration images for Hailo and AI Camera compilation are currently dummy frames. Real dataset support is pending.
- Compilers for `rpi` (TFLite) and `jetson_orin_nano` (TensorRT) are stubs.
- No deployment rollback if `deploy_failed`.
- No real-time log streaming from edge devices to the UI.
