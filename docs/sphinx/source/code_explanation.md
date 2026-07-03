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
├── data/                       # Local volume mounts for databases (git-ignored)
├── docker/                     # Per-service compose files and setup configurations
├── docs/                       # Project documentation (Sphinx & TypeDoc configurations)
├── services/                   # Server backend microservices (gRPC/REST/MQTT listeners)
├── edge-runtime/               # Python-based agent code running on edge devices
├── frontend/                   # Next.js 15 frontend application (App Router)
├── shared/                     # Shared modules, utility code, and generated gRPC stubs
└── hardware/                   # Custom hardware definitions, peripherals, and tempThe server-side system runs separate backend microservices interacting via gRPC, exposed to the web frontend through the API Gateway.
```

### `services/api-gateway/`
Acts as the single REST entry point. Resolves authentication, maps routes, and proxies requests to internal gRPC endpoints.

| File / Component | Description |
|---|---|
| [app/main.py](code_docs/api_gateway_service_main.rst) | Initializes the FastAPI application, mounts CORS configurations, and binds REST routers. |
| [app/config.py](code_docs/api_gateway_service_config.rst) | Declares and validates configuration parameters (ports, hosts, JWT secrets). |
| [app/stubs.py](code_docs/api_gateway_service_stubs.rst) | Implements cached gRPC channel stubs singleton connection pool. |
| [app/auth/jwt.py](code_docs/api_gateway_service_auth_jwt.rst) | Implements JWT token signing, verification, and mock user validation. |
| [app/routers/datasets.py](code_docs/api_gateway_service_routers_datasets.rst) | Handles dataset zip validation and S3 uploads. |
| [app/routers/deployments.py](code_docs/api_gateway_service_routers_deployments.rst) | Manages OTA deployment lifecycle and triggers. |
| [app/routers/devices.py](code_docs/api_gateway_service_routers_devices.rst) | Manages device registration and queries peripheral catalogs. |
| [app/routers/models.py](code_docs/api_gateway_service_routers_models.rst) | Handles ML model uploads and compiler activation. |
| [app/routers/monitoring.py](code_docs/api_gateway_service_routers_monitoring.rst) | Establishes telemetry queries and historical inference endpoints. |
| [app/routers/scripts.py](code_docs/api_gateway_service_routers_scripts.rst) | Handles user-defined inference scripts registration. |

### `services/registry-service/`
Acts as the metadata catalog. Persists data about registered hardware, uploaded model assets, and scripts.

| File / Component | Description |
|---|---|
| [app/main.py](code_docs/registry_service_main.rst) | Instantiates and starts the registry service gRPC listener on port `50051`. |
| [app/config.py](code_docs/registry_service_config.rst) | Service settings loader. |
| [app/update_existing_datasets.py](code_docs/registry_service_update_existing_datasets.rst) | Migration scripts to bootstrap database datasets logic. |
| [app/grpc_handlers/ai_handler.py](code_docs/registry_service_grpc_handlers_ai_handler.rst) | Resolves RPCs relating to models registration, dataset files, and compiler reports. |
| [app/grpc_handlers/device_handler.py](code_docs/registry_service_grpc_handlers_device_handler.rst) | Resolves RPCs relating to device registrations, updates, and deletes. |
| [app/grpc_handlers/script_handler.py](code_docs/registry_service_grpc_handlers_script_handler.rst) | Resolves RPCs relating to script file catalog storage. |
| [app/repositories/devices.py](code_docs/registry_service_repositories_devices.rst) | PostgreSQL DB queries interface for device records. |
| [app/repositories/models.py](code_docs/registry_service_repositories_models.rst) | PostgreSQL DB queries interface for models and datasets records. |
| [app/repositories/scripts.py](code_docs/registry_service_repositories_scripts.rst) | PostgreSQL DB queries interface for scripts metadata. |
| [app/models/orm.py](code_docs/registry_service_models_orm.rst) | SQLAlchemy ORM classes mapping database tables (`devices`, `models`, `scripts`, `deployments`). |

### `services/mlops-service/`
Runs asynchronous compilation and optimization pipelines using isolated Docker runtimes.

| File / Component | Description |
|---|---|
| [app/main.py](code_docs/mlops_service_main.rst) | Starts the gRPC compilation listener server on port `50052`. |
| [app/config.py](code_docs/mlops_service_config.rst) | MLOps environmental parameters validation settings. |
| [app/worker.py](code_docs/mlops_service_worker.rst) | ARQ Redis worker processing compiled models and yolo training runs. |
| [app/grpc_handlers/compilation_handler.py](code_docs/mlops_service_grpc_handlers_compilation_handler.rst) | Listens to and launches job compilation requests. |
| [app/compilers/base.py](code_docs/mlops_service_compilers_base.rst) | Defines abstract `CompilerBase` interface and Redis logs streamer tools. |
| [app/compilers/yolo_train.py](code_docs/mlops_service_compilers_yolo_train.rst) | Pipeline trigger that executes YOLOv8 model training. |

### `services/edge-connector-service/`
Connects the cloud services to the physical hardware devices.

| File / Component | Description |
|---|---|
| [app/main.py](code_docs/edge_connector_service_main.rst) | Entry point starting the gRPC connector server on port `50053` and the Prometheus metrics exporter on port `9100`. |
| [app/config.py](code_docs/edge_connector_service_config.rst) | Service database and broker credentials validation. |
| [app/worker.py](code_docs/edge_connector_service_worker.rst) | ARQ queue worker monitoring active deployments status. |
| [app/grpc_handlers/deployment_handler.py](code_docs/edge_connector_service_grpc_handlers_deployment_handler.rst) | Handles RPCs for scheduling OTA deployments. |
| [app/grpc_handlers/monitoring_handler.py](code_docs/edge_connector_service_grpc_handlers_monitoring_handler.rst) | Handles RPC queries retrieving active telemetry statuses. |
| [app/mqtt/listener.py](code_docs/edge_connector_service_mqtt_listener.rst) | MQTT loop client ingesting telemetry, acknowledgements, and inference payloads. |
| [app/models/orm.py](code_docs/edge_connector_service_models_orm.rst) | SQLAlchemy structures tracking active deployments. |
| [app/models/mongo.py](code_docs/edge_connector_service_models_mongo.rst) | Time-series metrics document structures. |
| [app/repositories/deployments.py](code_docs/edge_connector_service_repositories_deployments.rst) | Query interface for deployment statuses. |
| [app/repositories/monitoring.py](code_docs/edge_connector_service_repositories_monitoring.rst) | Ingest log controller inserting states to MongoDB and updating Prometheus gauges. |

---

## 2. Edge Agent (`edge-runtime/`)

Designed to run locally on the physical target computer (e.g., Raspberry Pi 5).

| File / Component | Description |
|---|---|
| [edge-runtime/agent.py](code_docs/edge_runtime_agent.rst) | Main client entrypoint launching MQTT subscriptions, periodic telemetry updates, and active inference runtime loops. |
| [edge-runtime/hardware_daemon.py](code_docs/edge_runtime_hardware_daemon.rst) | Host-level HTTP server exposing cameras and accelerators natively to Docker containers. |
| [aura_hw/detect.py](code_docs/edge_runtime_aura_hw_detect.rst) | Probes host system hardware to detect connected accelerators (Hailo, IMX500, Jetson, CPU). |
| [aura_hw/device_manager.py](code_docs/edge_runtime_aura_hw_device_manager.rst) | Controls dynamic sensor configuration and peripheral drivers instantiation. |
| [aura_hw/loader.py](code_docs/edge_runtime_aura_hw_loader.rst) | Dynamically compiles and loads the user's inference script in memory. |
| [aura_hw/runtime.py](code_docs/edge_runtime_aura_hw_runtime.rst) | Public hardware interfaces managing model execution backends. |
| [pal/comm_client.py](code_docs/edge_runtime_pal_comm_client.rst) | Stable MQTT wrapper client mapping telemetry payload conventions. |
| [pal/orchestrator.py](code_docs/edge_runtime_pal_orchestrator.rst) | Handles parallel telemetry metrics and inference loops execution. |
| [pal/ota_handler.py](code_docs/edge_runtime_pal_ota_handler.rst) | Manages secure HTTP downloads of model files and executes SHA-256 integrity validation checks. |

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

| File / Component | Description |
|---|---|
| [shared/proto_gen/](code_docs/shared_transport.rst) | Generated Protocol Buffer Python message stubs and services bindings. |
| [shared/transport/base.py](code_docs/shared_transport_base.rst) | Defines abstract transport layers interfaces. |
| [shared/transport/mqtt.py](code_docs/shared_transport_mqtt.rst) | Reusable MQTT connection and publish wrappers logic. |
| [shared/utils/database.py](code_docs/shared_utils_database.rst) | Shared SQLAlchemy engine connection context helpers. |
| [shared/utils/minio.py](code_docs/shared_utils_minio.rst) | Wraps client logic for presigned URL signatures and uploads. |
| [shared/utils/logging.py](code_docs/shared_utils_logging.rst) | Unified format configuration settings for all console outputs. |
| [shared/utils/grpc_server.py](code_docs/shared_utils_grpc_server.rst) | Core listener startup helper wrapping standard gRPC parameters. |

---

## 5. Physical Hardware Integration (`hardware/`)

Additional hardware modules:

* **`hardware/sensors/` & `hardware/actuators/`**: Simulators and physical libraries to run checks on temperature sensors, buzzer circuits, and LED modules.
* **`hardware/hw_arch/`**: Hardware compiler configurations and calibration utilities.

---

## Technical Module Reference

The following list contains all dynamically scanned modules automatically documented from the platform source code:

```{toctree}
:hidden:
:maxdepth: 1

   code_docs/api_gateway_service_auth_jwt
   code_docs/api_gateway_service_config
   code_docs/api_gateway_service_main
   code_docs/api_gateway_service_routers_datasets
   code_docs/api_gateway_service_routers_deployments
   code_docs/api_gateway_service_routers_devices
   code_docs/api_gateway_service_routers_models
   code_docs/api_gateway_service_routers_monitoring
   code_docs/api_gateway_service_routers_scripts
   code_docs/api_gateway_service_stubs
   code_docs/edge_connector_service_config
   code_docs/edge_connector_service_grpc_handlers_deployment_handler
   code_docs/edge_connector_service_grpc_handlers_monitoring_handler
   code_docs/edge_connector_service_main
   code_docs/edge_connector_service_models_mongo
   code_docs/edge_connector_service_models_orm
   code_docs/edge_connector_service_mqtt_listener
   code_docs/edge_connector_service_repositories_deployments
   code_docs/edge_connector_service_repositories_monitoring
   code_docs/edge_connector_service_worker
   code_docs/edge_runtime_agent
   code_docs/edge_runtime_aura_hw
   code_docs/edge_runtime_aura_hw_backends_base
   code_docs/edge_runtime_aura_hw_backends_devices
   code_docs/edge_runtime_aura_hw_backends_devices_actuator
   code_docs/edge_runtime_aura_hw_backends_devices_actuator_base
   code_docs/edge_runtime_aura_hw_backends_devices_actuator_general
   code_docs/edge_runtime_aura_hw_backends_devices_base
   code_docs/edge_runtime_aura_hw_backends_devices_camera
   code_docs/edge_runtime_aura_hw_backends_devices_camera_base
   code_docs/edge_runtime_aura_hw_backends_devices_camera_general
   code_docs/edge_runtime_aura_hw_backends_devices_other
   code_docs/edge_runtime_aura_hw_backends_devices_other_base
   code_docs/edge_runtime_aura_hw_backends_devices_other_general
   code_docs/edge_runtime_aura_hw_backends_devices_sensor
   code_docs/edge_runtime_aura_hw_backends_devices_sensor_base
   code_docs/edge_runtime_aura_hw_backends_devices_sensor_general
   code_docs/edge_runtime_aura_hw_backends_inference
   code_docs/edge_runtime_aura_hw_backends_inference_base
   code_docs/edge_runtime_aura_hw_backends_inference_general
   code_docs/edge_runtime_aura_hw_detect
   code_docs/edge_runtime_aura_hw_device_manager
   code_docs/edge_runtime_aura_hw_loader
   code_docs/edge_runtime_aura_hw_runtime
   code_docs/edge_runtime_daemon
   code_docs/edge_runtime_daemon_camera
   code_docs/edge_runtime_daemon_hailo
   code_docs/edge_runtime_daemon_imx500
   code_docs/edge_runtime_daemon_shared
   code_docs/edge_runtime_hardware_daemon
   code_docs/edge_runtime_pal
   code_docs/edge_runtime_pal_comm_client
   code_docs/edge_runtime_pal_orchestrator
   code_docs/edge_runtime_pal_ota_handler
   code_docs/mlops_service_actuators
   code_docs/mlops_service_compilers
   code_docs/mlops_service_compilers_base
   code_docs/mlops_service_compilers_yolo_train
   code_docs/mlops_service_config
   code_docs/mlops_service_grpc_handlers_compilation_handler
   code_docs/mlops_service_main
   code_docs/mlops_service_models_orm
   code_docs/mlops_service_others
   code_docs/mlops_service_repositories_compilation
   code_docs/mlops_service_sensors
   code_docs/mlops_service_worker
   code_docs/registry_service_config
   code_docs/registry_service_grpc_handlers_ai_handler
   code_docs/registry_service_grpc_handlers_device_handler
   code_docs/registry_service_grpc_handlers_script_handler
   code_docs/registry_service_main
   code_docs/registry_service_models_orm
   code_docs/registry_service_repositories_devices
   code_docs/registry_service_repositories_models
   code_docs/registry_service_repositories_scripts
   code_docs/registry_service_update_existing_datasets
   code_docs/shared_transport
   code_docs/shared_transport_base
   code_docs/shared_transport_mqtt
   code_docs/shared_utils_database
   code_docs/shared_utils_grpc_server
   code_docs/shared_utils_logging
   code_docs/shared_utils_minio
```
