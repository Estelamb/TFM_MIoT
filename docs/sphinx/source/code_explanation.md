# Codebase Structure and Explanation

This section provides a detailed walk-through of the **AURA Platform** codebase structure. It highlights the main directories, microservices, files, and classes to help developers navigate the project.

---

## High-Level Repository Layout

AURA is architected as a set of loosely coupled microservices communicating via **gRPC** internally, with an independent Python **Edge Agent** and a Next.js frontend web dashboard.

```
TFM_MIoT/
├── .env.example                # Global template for environment variables
├── docker-compose.yml          # Container orchestration file for server stack & infra
├── README.md                   # Unified project overview, quick start, running guide, and developer guide
├── docs/                       # Project documentation (Sphinx & TypeDoc configurations)
├── services/                   # Server backend microservices (gRPC/REST/MQTT listeners)
├── edge-runtime/               # Python-based agent code running on edge devices
├── frontend/                   # Next.js 15 frontend application (App Router)
├── shared/                     # Shared modules, utility code, and generated gRPC stubs
└── hardware/                   # Custom hardware definitions, peripherals, and tempThe server-side system runs separate backend microservices interacting via gRPC, exposed to the web frontend through the API Gateway.
```

### `services/api-gateway/`
Acts as the single REST entry point. Resolves authentication, maps routes, and proxies requests to internal gRPC endpoints.

| File / Component | Folder | Description |
|---|---|---|
| [main.py](code_docs/api_gateway_service_main.rst) | `services/api-gateway/app` | Initializes the FastAPI application, mounts CORS configurations, and binds REST routers. |
| [config.py](code_docs/api_gateway_service_config.rst) | `services/api-gateway/app` | Declares and validates configuration parameters (ports, hosts, JWT secrets). |
| [stubs.py](code_docs/api_gateway_service_stubs.rst) | `services/api-gateway/app` | Implements cached gRPC channel stubs singleton connection pool. |
| [jwt.py](code_docs/api_gateway_service_auth_jwt.rst) | `services/api-gateway/app/auth` | Implements JWT token signing, verification, and mock user validation. |
| [datasets.py](code_docs/api_gateway_service_routers_datasets.rst) | `services/api-gateway/app/routers` | Handles dataset zip validation and S3 uploads. |
| [deployments.py](code_docs/api_gateway_service_routers_deployments.rst) | `services/api-gateway/app/routers` | Manages OTA deployment lifecycle and triggers. |
| [devices.py](code_docs/api_gateway_service_routers_devices.rst) | `services/api-gateway/app/routers` | Manages device registration and queries peripheral catalogs. |
| [models.py](code_docs/api_gateway_service_routers_models.rst) | `services/api-gateway/app/routers` | Handles ML model uploads and compiler activation. |
| [monitoring.py](code_docs/api_gateway_service_routers_monitoring.rst) | `services/api-gateway/app/routers` | Establishes telemetry queries and historical inference endpoints. |
| [scripts.py](code_docs/api_gateway_service_routers_scripts.rst) | `services/api-gateway/app/routers` | Handles user-defined inference scripts registration. |

### `services/registry-service/`
Acts as the metadata catalog. Persists data about registered hardware, uploaded model assets, and scripts.

| File / Component | Folder | Description |
|---|---|---|
| [main.py](code_docs/registry_service_main.rst) | `services/registry-service/app` | Instantiates and starts the registry service gRPC listener on port `50051`. |
| [config.py](code_docs/registry_service_config.rst) | `services/registry-service/app` | Service settings loader. |
| [update_existing_datasets.py](code_docs/registry_service_update_existing_datasets.rst) | `services/registry-service/app` | Migration scripts to bootstrap database datasets logic. |
| [ai_handler.py](code_docs/registry_service_grpc_handlers_ai_handler.rst) | `services/registry-service/app/grpc_handlers` | Resolves RPCs relating to models registration, dataset files, and compiler reports. |
| [device_handler.py](code_docs/registry_service_grpc_handlers_device_handler.rst) | `services/registry-service/app/grpc_handlers` | Resolves RPCs relating to device registrations, updates, and deletes. |
| [script_handler.py](code_docs/registry_service_grpc_handlers_script_handler.rst) | `services/registry-service/app/grpc_handlers` | Resolves RPCs relating to script file catalog storage. |
| [devices.py](code_docs/registry_service_repositories_devices.rst) | `services/registry-service/app/repositories` | PostgreSQL DB queries interface for device records. |
| [models.py](code_docs/registry_service_repositories_models.rst) | `services/registry-service/app/repositories` | PostgreSQL DB queries interface for models and datasets records. |
| [scripts.py](code_docs/registry_service_repositories_scripts.rst) | `services/registry-service/app/repositories` | PostgreSQL DB queries interface for scripts metadata. |
| [orm.py](code_docs/registry_service_models_orm.rst) | `services/registry-service/app/models` | SQLAlchemy ORM classes mapping database tables (`devices`, `models`, `scripts`, `deployments`). |

### `services/mlops-service/`
Runs asynchronous compilation and optimization pipelines using isolated Docker runtimes.

| File / Component | Folder | Description |
|---|---|---|
| [main.py](code_docs/mlops_service_main.rst) | `services/mlops-service/app` | Starts the gRPC compilation listener server on port `50052`. |
| [config.py](code_docs/mlops_service_config.rst) | `services/mlops-service/app` | MLOps environmental parameters validation settings. |
| [worker.py](code_docs/mlops_service_worker.rst) | `services/mlops-service/app` | ARQ Redis worker processing compiled models and yolo training runs. |
| [compilation_handler.py](code_docs/mlops_service_grpc_handlers_compilation_handler.rst) | `services/mlops-service/app/grpc_handlers` | Listens to and launches job compilation requests. |
| [base.py](code_docs/mlops_service_compilers_base.rst) | `services/mlops-service/app/compilers` | Defines abstract `CompilerBase` interface and Redis logs streamer tools. |
| [yolo_train.py](code_docs/mlops_service_compilers_yolo_train.rst) | `services/mlops-service/app/compilers` | Pipeline trigger that executes YOLOv8 model training. |

### `services/edge-connector-service/`
Connects the cloud services to the physical hardware devices.

| File / Component | Folder | Description |
|---|---|---|
| [main.py](code_docs/edge_connector_service_main.rst) | `services/edge-connector-service/app` | Entry point starting the gRPC connector server on port `50053` and the Prometheus metrics exporter on port `9100`. |
| [config.py](code_docs/edge_connector_service_config.rst) | `services/edge-connector-service/app` | Service database and broker credentials validation. |
| [worker.py](code_docs/edge_connector_service_worker.rst) | `services/edge-connector-service/app` | ARQ queue worker monitoring active deployments status. |
| [deployment_handler.py](code_docs/edge_connector_service_grpc_handlers_deployment_handler.rst) | `services/edge-connector-service/app/grpc_handlers` | Handles RPCs for scheduling OTA deployments. |
| [monitoring_handler.py](code_docs/edge_connector_service_grpc_handlers_monitoring_handler.rst) | `services/edge-connector-service/app/grpc_handlers` | Handles RPC queries retrieving active telemetry statuses. |
| [listener.py](code_docs/edge_connector_service_mqtt_listener.rst) | `services/edge-connector-service/app/mqtt` | MQTT loop client ingesting telemetry, acknowledgements, and inference payloads. |
| [orm.py](code_docs/edge_connector_service_models_orm.rst) | `services/edge-connector-service/app/models` | SQLAlchemy structures tracking active deployments. |
| [mongo.py](code_docs/edge_connector_service_models_mongo.rst) | `services/edge-connector-service/app/models` | Time-series metrics document structures. |
| [deployments.py](code_docs/edge_connector_service_repositories_deployments.rst) | `services/edge-connector-service/app/repositories` | Query interface for deployment statuses. |
| [monitoring.py](code_docs/edge_connector_service_repositories_monitoring.rst) | `services/edge-connector-service/app/repositories` | Ingest log controller inserting states to MongoDB and updating Prometheus gauges. |

---

## 2. Edge Agent (`edge-runtime/`)

Designed to run locally on the physical target computer (e.g., Raspberry Pi 5).

| File / Component | Folder | Description |
|---|---|---|
| [agent.py](code_docs/edge_runtime_agent.rst) | `edge-runtime` | Main client entrypoint launching MQTT subscriptions, periodic telemetry updates, and active inference runtime loops. |
| [hardware_daemon.py](code_docs/edge_runtime_hardware_daemon.rst) | `edge-runtime` | Host-level HTTP server exposing cameras and accelerators natively to Docker containers. |
| [detect.py](code_docs/edge_runtime_aura_hw_detect.rst) | `edge-runtime/aura_hw` | Probes host system hardware to detect connected accelerators (Hailo, IMX500, CPU). |
| [device_manager.py](code_docs/edge_runtime_aura_hw_device_manager.rst) | `edge-runtime/aura_hw` | Controls dynamic sensor configuration and peripheral drivers instantiation. |
| [loader.py](code_docs/edge_runtime_aura_hw_loader.rst) | `edge-runtime/aura_hw` | Dynamically compiles and loads the user's inference script in memory. |
| [runtime.py](code_docs/edge_runtime_aura_hw_runtime.rst) | `edge-runtime/aura_hw` | Public hardware interfaces managing model execution backends. |
| [comm_client.py](code_docs/edge_runtime_pal_comm_client.rst) | `edge-runtime/pal` | Stable MQTT wrapper client mapping telemetry payload conventions. |
| [orchestrator.py](code_docs/edge_runtime_pal_orchestrator.rst) | `edge-runtime/pal` | Handles parallel telemetry metrics and inference loops execution. |
| [ota_handler.py](code_docs/edge_runtime_pal_ota_handler.rst) | `edge-runtime/pal` | Manages secure HTTP downloads of model files and executes SHA-256 integrity validation checks. |

---

## 3. Frontend Web Dashboard (`frontend/`)

Built using **Next.js 16** (TypeScript, Tailwind CSS, TanStack Query).

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

| File / Component | Folder | Description |
|---|---|---|
| [proto_gen/](code_docs/shared_transport.rst) | `shared` | Generated Protocol Buffer Python message stubs and services bindings. |
| [base.py](code_docs/shared_transport_base.rst) | `shared/transport` | Defines abstract transport layers interfaces. |
| [mqtt.py](code_docs/shared_transport_mqtt.rst) | `shared/transport` | Reusable MQTT connection and publish wrappers logic. |
| [database.py](code_docs/shared_utils_database.rst) | `shared/utils` | Shared SQLAlchemy engine connection context helpers. |
| [minio.py](code_docs/shared_utils_minio.rst) | `shared/utils` | Wraps client logic for presigned URL signatures and uploads. |
| [logging.py](code_docs/shared_utils_logging.rst) | `shared/utils` | Unified format configuration settings for all console outputs. |
| [grpc_server.py](code_docs/shared_utils_grpc_server.rst) | `shared/utils` | Core listener startup helper wrapping standard gRPC parameters. |

---

## 5. Physical Hardware Integration (`hardware/`)

Additional hardware modules:

* **`hardware/sensors/` & `hardware/actuators/`**: Simulators and physical libraries to run checks on temperature sensors, buzzer circuits, and LED modules.
* **`hardware/hw_arch/`**: Hardware compiler configurations and calibration utilities.


