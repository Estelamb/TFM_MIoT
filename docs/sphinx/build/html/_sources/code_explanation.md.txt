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
* [api-gateway/app/main.py](file:///c:/Users/Estela/TFM_MIoT/services/api-gateway/app/main.py): Initializes the FastAPI application, mounts CORS middlewares, and binds REST routers.
* [api-gateway/app/config.py](file:///c:/Users/Estela/TFM_MIoT/services/api-gateway/app/config.py): Validates configurations (JWT secrets, internal gRPC host mappings).
* [api-gateway/app/stubs.py](file:///c:/Users/Estela/TFM_MIoT/services/api-gateway/app/stubs.py): Caches active gRPC channels to communicate with backends.
* **`app/auth/`**: Contains utility functions to sign/decode JWT tokens and hash credentials.
* **`app/routers/`**: Exposes REST paths by calling internal gRPC channels:
  * `deployments.py`: Manages the lifecycle of deployments and releases.
  * `devices.py`: Manages device metadata and connection states.
  * `models.py`: Handles model uploads and compilation triggers.
  * `scripts.py`: Manages inference script files.
  * `monitoring.py`: Implements real-time telemetry WebSocket endpoints.

### `services/registry-service/`
Acts as the metadata catalog. Persists data about registered hardware, uploaded model assets, and scripts.
* [registry-service/app/main.py](file:///c:/Users/Estela/TFM_MIoT/services/registry-service/app/main.py): Sets up and runs the gRPC server on port `50051`.
* **`app/grpc_handlers/`**: Handles RPC calls to fetch/modify devices, models, and scripts.
* **`app/repositories/`**: Implements Repository patterns using SQLAlchemy to perform PostgreSQL operations.
* **`app/models/`**: SQL schemas mapped via SQLAlchemy ORM classes.

### `services/mlops-service/`
Runs asynchronous compilation and optimization pipelines using isolated Docker runtimes.
* [mlops-service/app/main.py](file:///c:/Users/Estela/TFM_MIoT/services/mlops-service/app/main.py): Listens for gRPC compilation requests on port `50052`.
* [mlops-service/app/worker.py](file:///c:/Users/Estela/TFM_MIoT/services/mlops-service/app/worker.py): Manages compilation tasks and spawns local Docker container compilations using the Docker socket.
* **`app/compilers/`**: Contains compiler implementations (Hailo, TensorRT, TFLite).

### `services/edge-connector-service/`
Connects the cloud services to the physical hardware devices.
* [edge-connector-service/app/main.py](file:///c:/Users/Estela/TFM_MIoT/services/edge-connector-service/app/main.py): Initializes the service on port `50053`.
* [edge-connector-service/app/worker.py](file:///c:/Users/Estela/TFM_MIoT/services/edge-connector-service/app/worker.py): Listens to incoming MQTT metrics and telemetry, persisting them in MongoDB and Prometheus.
* **`app/mqtt/`**: MQTT client configuration and subscription loops.

---

## 2. Edge Agent (`edge-runtime/`)

Designed to run locally on the physical target computer (e.g., Raspberry Pi 5).

* [edge-runtime/agent.py](file:///c:/Users/Estela/TFM_MIoT/edge-runtime/agent.py): The edge agent entry point. Establishes the MQTT client connection, sends system metrics, downloads compiled model artifacts, verifies hashes, and starts the active inference loop.
* **`edge-runtime/pal/`**: Platform Abstraction Layer:
  * `comm_client.py`: Handles MQTT socket client interfaces and telemetry message publishing.
* **`edge-runtime/aura_hw/`**: Hardware abstraction library:
  * `detect.py`: Automatically runs hardware inspection commands to check which NPUs are attached.
  * `device_manager.py`: Controls low-level sensor interfaces, camera devices, and active actuators.
  * `loader.py`: Loads the user-submitted Python inference script dynamically into the Python runtime.
  * `runtime.py`: Coordinates model execution with the detected backend accelerator.
  * **`aura_hw/backends/`**: Specific backends for each compiler output target (Hailo, IMX500, CPU/TFLite, Jetson).

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
  * `database.py`: PostgreSQL connection utilities and session decorators.
  * `minio.py`: Helper class for MinIO S3 object storage (bucket operations, pre-signed URL creation).
  * `logging.py`: Centralized logging formatters.

---

## 5. Physical Hardware Integration (`hardware/`)

Additional hardware modules:

* **`hardware/sensors/` & `hardware/actuators/`**: Simulators and physical libraries to run checks on temperature sensors, buzzer circuits, and LED modules.
* **`hardware/hw_arch/`**: Hardware compiler configurations and calibration utilities.
