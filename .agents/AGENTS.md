# AURA Platform — Agent Guidelines (AGENTS.md)

Welcome! This file contains style guidelines, behavioral constraints, architecture descriptions, and implementation instructions for AI agents working on the **AURA Platform** codebase.

---

## 1. Project Architecture Overview

AURA is a modular MLOps and Edge AI deployment platform for IoT devices. It consists of:
*   **Frontend**: Next.js 16.2 + Tailwind CSS v4 + React Query + Zustand. Exposes the main dashboard at port 3000.
*   **api-gateway**: FastAPI service (port 8000) that acts as the entrypoint for the frontend and forwards requests to internal gRPC microservices.
*   **registry-service**: gRPC service (port 50051) storing devices, models, and scripts metadata in PostgreSQL (via SQLAlchemy) and binary artifacts in MinIO S3.
*   **mlops-service**: gRPC service (port 50052) that runs compilation and YOLOv8 training tasks asynchronously via an ARQ Redis queue/worker process.
*   **edge-connector-service**: gRPC service (port 50053) that manages MQTT events, ingests telemetry, updates device online status, and handles OTA deployments.
*   **edge-runtime**: Python runtime running on edge devices. Includes `agent.py` to handle MQTT events, retrieve deployments via presigned MinIO URLs, and perform live inference.

---

## 2. Directory Layout & File References

*   [docker-compose.yml](file:///c:/Users/Estela/TFM_MIoT/docker-compose.yml): Runs the full stack locally.
*   [shared/proto/](file:///c:/Users/Estela/TFM_MIoT/shared/proto): Source of truth Protobuf API definitions.
*   [shared/proto_gen/](file:///c:/Users/Estela/TFM_MIoT/shared/proto_gen): Generated Python gRPC stubs. **Never edit files in this directory manually.**
*   [shared/utils/](file:///c:/Users/Estela/TFM_MIoT/shared/utils): Database connection management, logging setup, and MinIO client helpers.
*   [services/](file:///c:/Users/Estela/TFM_MIoT/services): The microservices backend (`api-gateway`, `registry-service`, `mlops-service`, `edge-connector-service`).
*   [hardware/](file:///c:/Users/Estela/TFM_MIoT/hardware): Core hardware compilers and drivers catalog:
    *   `hw_arch/`: Hardware compilers registry (Hailo, RPi CPU, RPi AI Camera, etc.).
    *   `sensors/`: Peripheral sensors wrapper drivers (Camera, BME280, template, etc.).
    *   `actuators/`: Peripheral actuators wrapper drivers (LED, relays, etc.).
*   [edge-runtime/](file:///c:/Users/Estela/TFM_MIoT/edge-runtime): IoT edge daemon agent, hardware abstraction layers, and local device configuration.
*   [frontend/](file:///c:/Users/Estela/TFM_MIoT/frontend): Next.js single-page application.

---

## 3. Protocol Buffer & gRPC Compilation

gRPC protocol definitions inside [shared/proto/](file:///c:/Users/Estela/TFM_MIoT/shared/proto) are the source of truth for all API communication.
Whenever you modify a `.proto` file:
1.  Run the Python compilation script:
    ```powershell
    python scripts/compile_proto.py
    ```
2.  The script will regenerate files in [shared/proto_gen/](file:///c:/Users/Estela/TFM_MIoT/shared/proto_gen) and automatically adjust relative module imports (e.g., rewriting `import xxx_pb2` to `from shared.proto_gen import xxx_pb2`). Always verify the changes to the generated Python files are correct.

---

## 4. Hardware Compilers Protocol (`hardware/hw_arch`)

Model compilation for AI accelerators is dynamically scanned and registered from the [hardware/hw_arch/](file:///c:/Users/Estela/TFM_MIoT/hardware/hw_arch) subdirectories.

### Key Rules for Adding/Modifying Compilers:
1.  **Compiler Class**: Every compiler must be declared in `hardware/hw_arch/<arch_name>/compilation/compiler.py` and subclass `CompilerBase` from [services/mlops-service/app/compilers/base.py](file:///c:/Users/Estela/TFM_MIoT/services/mlops-service/app/compilers/base.py).
2.  **Metadata Fields**:
    *   `LABEL`: Module-level string naming the compiler target (e.g. `LABEL = "Hailo-10"`).
    *   `EXECUTION_STRATEGY`: Either `"docker"` (runs in a separate Docker container via CLI command) or `"python"` (runs natively inside python process).
    *   `DOCKER_IMAGE`: The tag of the Docker image required (empty for `"python"` strategy).
    *   `OUTPUT_FORMAT`: The compiled file extension (e.g. `".hef"`, `".onnx"`).
    *   `SUPPORTED_HARDWARE`: List of strings matching target hardware types.
3.  **Compile Method**: Implement `async def compile(...) -> CompilationResult`.
    *   Fetch the `.pt` source file from MinIO `models` bucket.
    *   Execute compilation (e.g. using `asyncio.create_subprocess_exec` to call Docker compiler images).
    *   Upload the resulting compiled binary to MinIO `compiled` bucket.
    *   Return a `CompilationResult(success=True, compiled_key=..., compiled_sha256=...)` or `success=False` with error message.

---

## 5. Sensors, Actuators & Others Drivers Protocol (`hardware/sensors`, `hardware/actuators` & `hardware/others`)

AURA scans peripherals dynamically to display them in the catalog and load their drivers in the Edge Agent.

### Directory Convention:
*   Sensors: `hardware/sensors/<category>/<peripheral_name>/library.py`
*   Actuators: `hardware/actuators/<category>/<peripheral_name>/library.py`
*   Others: `hardware/others/<category>/<peripheral_name>/library.py`

### Guidelines:
1.  **Friendly Label**: Each driver's `library.py` must define a global `LABEL = "Friendly Device Name"`.
2.  **Wrappers**: Category-level wrappers (like [hardware/sensors/camera/library.py](file:///c:/Users/Estela/TFM_MIoT/hardware/sensors/camera/library.py)) should:
    *   Read active driver and parameters from `components_config.yaml` using `get_active_driver`.
    *   Load the actual class using `load_specific_driver` dynamically.
    *   Delegate interface methods (`initialize`, `read_value`, `close`) to the underlying active driver class.
3.  **Mock Failback**: If a driver's native package is missing (e.g. `picamera2` is only present on actual Raspberry Pi hardware), fall back gracefully to a mock or simulated driver to allow local testing.

---

## 6. Coding Standards & Conventions

### Python Backend Rules:
*   **Non-Blocking Event Loop**: Never execute long CPU/IO-bound blocking operations directly in the async handlers. Use `await asyncio.to_thread(func, ...)` or delegate them to background `arq` worker jobs (`train_job` and `compile_job` in [services/mlops-service/app/worker.py](file:///c:/Users/Estela/TFM_MIoT/services/mlops-service/app/worker.py)).
*   **Database Session Management**: Ensure database async sessions (`AsyncSession`) are properly closed or handled inside lifecycle hooks or context managers.
*   **Idempotency Keys**: Use `_job_id` when enqueueing `arq` jobs to prevent spawning duplicate compilation or training tasks for the same model.

### Frontend Development Rules:
*   **Framework**: Next.js 16.2 App Router. Layouts and routes are organized under the `app/` directory.
*   **Styling**: Use Vanilla CSS variables and Tailwind CSS v4 color/utility classes. Theme toggling is handled via `next-themes`.
*   **State Management**: Custom lightweight states are stored in Zustand stores (`frontend/hooks/` or `frontend/lib/`).
*   **API Ingestion**: Rely on TanStack React Query (`@tanstack/react-query`) for fetch queries, mutations, caching, and auto-refetch polling triggers (5-10s interval for telemetry updates).
*   **Mock Credentials**: Auth for PoC uses hardcoded credentials (`admin` / `aura2026`).

---

## 7. Running & Testing Locally

1.  **Docker Stack Setup**:
    ```bash
    docker compose up -d --build
    ```
2.  **API Test Reflections**: Use gRPCurl or gRPC Client tools to test reflection services exposed at ports `50051` (Registry), `50052` (MLOps), and `50053` (Edge Connector).
3.  **Local Python Docs**:
    *   Sphinx Docs: Compile using `python -m sphinx.cmd.build -M html docs/sphinx/source docs/sphinx/build`
    *   TypeDoc Docs: Run `npx typedoc --options ../docs/typedoc/typedoc.json` inside the `frontend/` directory.
