# Codebase Structure and Explanation

This section provides a detailed walk-through of the **AURA Platform** codebase structure. It highlights the main directories, microservices, files, and classes to help developers navigate the project.

---

## High-Level Repository Layout

AURA is architected as a set of loosely coupled microservices communicating via **gRPC** internally, with an independent Python **Edge Agent** and a Next.js frontend web dashboard.

```
TFM_MIoT/
├── .env.example                # Global template for environment variables
├── docker-compose.yml          # Container orchestration file for server stack & infra
├── README.md                   # Project overview and introduction
├── RUNNING.md                  # Comprehensive platform execution guide
├── DEVELOPER_GUIDE.md          # Guide for adding new compilers and hardware architectures
├── data/                       # Local volume mounts for databases (git-ignored)
├── docker/                     # Per-service compose files and setup configurations
├── docs/                       # Project documentation (Sphinx & TypeDoc configurations)
├── services/                   # Server backend microservices (gRPC/REST/MQTT listeners)
├── edge-runtime/               # Python-based agent code running on edge devices
├── frontend/                   # Next.js 15 frontend application (App Router)
├── shared/                     # Shared modules, utility code, and generated gRPC stubs
└── hardware/                   # Custom hardware definitions, peripherals, and templates
```

---

## 1. Backend Microservices (`services/`)

The server-side system runs separate backend microservices interacting via gRPC, exposed to the web frontend through the API Gateway.

### `services/api-gateway/`
Acts as the single REST entry point. Resolves authentication and proxies requests to internal gRPC endpoints.
* [api-gateway/app/main.py](autoapi/api_gateway_service/main/index): Initializes the FastAPI application, mounts CORS middlewares, and binds REST routers.
  ```python
  """API Gateway entry point.

  FastAPI application that acts as the single HTTP entry point for the
  frontend. Authenticates requests with JWT and proxies them to the
  appropriate downstream gRPC service. Handles multipart file uploads
  directly to MinIO to avoid passing large binaries through gRPC.
  """
  ```
* [api-gateway/app/config.py](autoapi/api_gateway_service/config/index): Validates configurations (JWT secrets, internal gRPC host mappings).
* [api-gateway/app/stubs.py](autoapi/api_gateway_service/stubs/index): Caches active gRPC channels to communicate with backends.
  ```python
  """gRPC stubs singleton for the gateway."""
  ```
* **[app/auth/](autoapi/api_gateway_service/auth/index)**: Contains utility functions to sign/decode JWT tokens and hash credentials.
  * [jwt.py](autoapi/api_gateway_service/auth/jwt/index):
    ```python
    """JWT authentication helpers for the API Gateway.

    Provides token creation and verification utilities, plus the hardcoded
    demo user. The demo user will be replaced with database-backed auth
    in a future iteration.
    """
    ```
* **[app/routers/](autoapi/api_gateway_service/routers/index)**: Exposes REST paths by calling internal gRPC channels:
  * [deployments.py](autoapi/api_gateway_service/routers/deployments/index): Manages the lifecycle of deployments and releases.
  * [devices.py](autoapi/api_gateway_service/routers/devices/index): Manages device metadata and connection states.
  * [models.py](autoapi/api_gateway_service/routers/models/index): Handles model uploads and compilation triggers.
  * [scripts.py](autoapi/api_gateway_service/routers/scripts/index): Manages inference script files.
  * [monitoring.py](autoapi/api_gateway_service/routers/monitoring/index): Implements real-time telemetry WebSocket endpoints.

### `services/registry-service/`
Acts as the metadata catalog. Persists data about registered hardware, uploaded model assets, and scripts.
* [registry-service/app/main.py](autoapi/registry_service/main/index): Sets up and runs the gRPC server on port `50051`.
  ```python
  """Registry Service entry point.

  Consolidates Device, AI, and Script metadata management.
  Starts a single async gRPC server on port 50051 that hosts
  DeviceServiceHandler, AIServiceHandler, and ScriptServiceHandler.
  """
  ```
* **[app/grpc_handlers/](autoapi/registry_service/grpc_handlers/index)**: Handles RPC calls to fetch/modify devices, models, and scripts.
* **[app/repositories/](autoapi/registry_service/repositories/index)**: Implements Repository patterns using SQLAlchemy to perform PostgreSQL operations.
* **[app/models/](autoapi/registry_service/models/index)**: SQL schemas mapped via SQLAlchemy ORM classes.

### `services/mlops-service/`
Runs asynchronous compilation and optimization pipelines using isolated Docker runtimes.
* [mlops-service/app/main.py](autoapi/mlops_service/main/index): Listens for gRPC compilation requests on port `50052`.
  ```python
  """Compilation Service entry point.

  Starts an async gRPC server on port 50054 that exposes
  :class:`~app.grpc_handlers.compilation_handler.CompilationServiceHandler`.
  Compilation jobs run as background asyncio tasks so the RPC returns immediately.
  """
  ```
* [mlops-service/app/worker.py](autoapi/mlops_service/worker/index): Manages compilation tasks and spawns local Docker container compilations using the Docker socket.
  ```python
  """ARQ worker for compilation-service.

  Defines job functions for:
    - train_job:   runs YOLO training subprocess, uploads best.pt to MinIO
    - compile_job: runs hardware-specific compiler, uploads artefact to MinIO

  Both jobs update the model status in ai-service via gRPC on completion.

  The worker runs inside the same Docker container as the gRPC server but as
  a separate process (started via arq app.worker.WorkerSettings).
  """
  ```
* **[app/compilers/](autoapi/mlops_service/compilers/index)**: Contains compiler implementations (Hailo, TensorRT, ONNX).

### `services/edge-connector-service/`
Connects the cloud services to the physical hardware devices.
* [edge-connector-service/app/main.py](autoapi/edge_connector_service/main/index): Initializes the service on port `50053`.
  ```python
  """Edge Connector Service entry point.

  Consolidates OTA deployment orchestration, telemetry monitoring,
  and Prometheus metrics. Launches gRPC server, Prometheus exporter,
  MQTT background listener, and deployment arq worker.
  """
  ```
* [edge-connector-service/app/worker.py](autoapi/edge_connector_service/worker/index): Listens to incoming MQTT metrics and telemetry, persisting them in MongoDB and Prometheus.
  ```python
  """ARQ worker for deployment-service.

  Defines compile_and_deploy_job: triggers compilation via compilation-service
  gRPC, then waits for the model to become ready by polling Redis (published
  by the compilation worker) rather than polling Postgres in a busy loop.
  """
  ```
* **[app/mqtt/](autoapi/edge_connector_service/mqtt/index)**: MQTT client configuration and subscription loops.

---

## 2. Edge Agent (`edge-runtime/`)

Designed to run locally on the physical target computer (e.g., Raspberry Pi 5).

* [edge-runtime/agent.py](autoapi/edge_runtime/agent/index): The edge agent entry point. Establishes the MQTT client connection, sends system metrics, downloads compiled model artifacts, verifies hashes, and starts the active inference loop.
  ```python
  """AURA Edge Agent — Entrypoint
  =============================
  Minimal entrypoint that wires together the PAL components:

  * :class:`~pal.comm_client.CommunicationClient` — MQTT publish/subscribe
  * :class:`~pal.ota_handler.OTAHandler`          — OTA deploy handler
  * :class:`~pal.orchestrator.Orchestrator`        — inference + telemetry loops
  * :class:`~aura_hw.device_manager.DeviceManager` — connected device backends

  Configuration (priority order)
  -------------------------------
  1. Environment variables
  2. config/device_config.yaml
  3. Built-in defaults

  MQTT Topics
  -----------
  Subscribe:  device/{DEVICE_ID}/commands
  Publish:    device/{DEVICE_ID}/events
              device/{DEVICE_ID}/telemetry
              device/{DEVICE_ID}/inference
  """
  ```
* **[edge-runtime/pal/](autoapi/edge_runtime/pal/index)**: Platform Abstraction Layer:
  * [comm_client.py](autoapi/edge_runtime/pal/comm_client/index): Handles MQTT socket client interfaces and telemetry message publishing.
    ```python
    """PAL — Communication Client
    ===========================
    Async MQTT wrapper that provides a stable publish/subscribe interface
    to the rest of the runtime, with automatic reconnection on broker
    failures.

    All MQTT topic conventions live here so the rest of the codebase never
    constructs raw topic strings.

    Topics
    ------
    Subscribe:
        device/{device_id}/commands

    Publish:
        device/{device_id}/events
        device/{device_id}/telemetry
        device/{device_id}/inference
    """
    ```
* **[edge-runtime/aura_hw/](autoapi/edge_runtime/aura_hw/index)**: Hardware abstraction library:
  * [detect.py](autoapi/edge_runtime/aura_hw/detect/index): Automatically runs hardware inspection commands to check which NPUs are attached.
    ```python
    """Hardware auto-detection for the AURA edge runtime.

    Probes the host system to determine which AI accelerator is available.
    The result is cached after the first call so repeated imports don't
    re-run the detection logic.

    Detection order
    ---------------
    1. AURA_HARDWARE_TYPE environment variable (override, highest priority)
    2. hailortcli fw-control identify → hailo8 / hailo8l
    3. /etc/nv_tegra_release → jetson_orin_nano
    4. libcamera-hello --list-cameras with imx500 in output → rpi_ai_cam
    5. /proc/device-tree/model containing raspberry → rpi
    6. Fallback → unknown
    """
    ```
  * [device_manager.py](autoapi/edge_runtime/aura_hw/device_manager/index): Controls low-level sensor interfaces, camera devices, and active actuators.
    ```python
    """AURA Device Manager
    =====================
    Reads components_config.yaml, instantiates the correct device
    backend for each enabled component, and manages their lifecycle.

    All device backends are loaded dynamically from the hardware/
    directory, which is populated via OTA when the device connects to
    the AURA platform.
    """
    ```
  * [loader.py](autoapi/edge_runtime/aura_hw/loader/index): Loads the user-submitted Python inference script dynamically into the Python runtime.
  * [runtime.py](autoapi/edge_runtime/aura_hw/runtime/index): Coordinates model execution with the detected backend accelerator.
    ```python
    """Public API for the AURA hardware abstraction layer.

    Exposes five functions for inference scripts and the PAL layer:

    * load_model        — load a compiled model onto the detected hardware
    * execute_inference — run one inference pass
    * unload_model      — release the model and free accelerator resources
    * get_hardware_info — return a dict describing the current hardware state
    * get_last_inference— return the result of the last inference pass
    """
    ```
  * **[aura_hw/backends/](autoapi/edge_runtime/aura_hw/backends/index)**: Specific backends for each compiler output target (Hailo, IMX500, CPU/ONNX, Jetson).

---

## 3. Frontend Web Dashboard (`frontend/`)

Built using **Next.js 15** (TypeScript, Tailwind CSS, TanStack Query).

* **`frontend/app/`**: App Router page components:
  * `layout.tsx` & `page.tsx`: Welcome dashboard and main navigation.
  * **`(app)/devices/`**: Displays registered edge devices and live connections.
  * **`(app)/models/`**: Manages model uploads and monitors active compilations.
  * **`(app)/scripts/`**: Repository for inference Python scripts.
  * **`(app)/deployments/`**: Form to configure and deploy assets OTA.
  * **`(app)/monitoring/`**: Graphic charts powered by WebSockets to monitor resources and inference frames in real time.
* **`frontend/components/`**: Modular UI elements (resource charts, modal windows, table views).
* **`frontend/hooks/`**: Custom React hooks handling state updates and WebSocket bindings.
* **`frontend/lib/`**: Axios client utility functions.

---

## 4. Shared Modules (`shared/`)

Common modules imported by both backend microservices and edge runtimes.

* **`shared/proto/`**: Standard Protocol Buffer definitions (`.proto`).
* **`shared/proto_gen/`**: Auto-generated gRPC code generated using `grpcio-tools`.
* **`shared/transport/`**: Common network wrappers (e.g., helper clients for secure MQTT connections).
* **`shared/utils/`**:
  * [database.py](autoapi/shared/utils/database/index): PostgreSQL connection utilities and session decorators.
    ```python
    """Database utilities shared across all AURA services.

    Provides SQLAlchemy async engine and session factory builders,
    plus a common declarative base for ORM models.
    """
    ```
  * [minio.py](autoapi/shared/utils/minio/index): Helper class for MinIO S3 object storage (bucket operations, pre-signed URL creation).
    ```python
    """MinIO async client helpers for AURA services.

    Wraps miniopy-async to provide initialisation, bucket bootstrapping,
    binary upload and presigned URL generation as simple module-level calls
    shared across all services.
    """
    ```
  * [logging.py](autoapi/shared/utils/logging/index): Centralized logging formatters.
    ```python
    """Structured logging configuration for all AURA services.

    Configures a consistent log format that includes the service name,
    making it easy to filter logs when running the full stack.
    """
    ```

---

## 5. Physical Hardware Integration (`hardware/`)

Additional hardware modules:

* **`hardware/sensors/` & `hardware/actuators/`**: Simulators and physical libraries to run checks on temperature sensors, buzzer circuits, and LED modules.
* **`hardware/hw_arch/`**: Hardware compiler configurations and calibration utilities.
