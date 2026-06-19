# Introduction to the AURA Project

Welcome to the official documentation for **AURA Platform**, a comprehensive, end-to-end platform designed to simplify and automate the deployment lifecycle of Machine Learning and Computer Vision models on Internet of Things (IoT) and edge devices.

## What is AURA?

AURA provides a robust and scalable infrastructure that enables ML engineers, developers, and integrators to manage and orchestrate Edge AI workflows with ease. The platform covers the following key phases:

1. **Upload and Registry**: Centralized registry for machine learning models (standard formats like PyTorch `.pt`) and custom Python inference scripts.
2. **Compilation and Optimization**: Automatic model compilation for target hardware architectures (such as Hailo-8, IMX500, ONNX, or TensorRT) via the MLOps service.
3. **Remote (Over-the-Air) Deployment**: Distribution of the optimized model and corresponding inference script to multiple edge devices over a secure network powered by the MQTT protocol.
4. **Monitoring and Telemetry**: Continuous tracking of hardware performance (CPU, RAM usage, temperature) and real-time streaming of inference results via visualization dashboards.

---

## System Architecture

The AURA ecosystem is divided into two primary blocks: the **Cloud/Server Platform** and the **Edge Runtime**.

```
                           +--------------------------------------+
                           |          Frontend Interface          |
                           |            (Next.js App)             |
                           +------------------+-------------------+
                                              | HTTP / JWT
                                              v
                           +------------------+-------------------+
                           |           API Gateway                |
                           |            (FastAPI)                 |
                           +--------+---------+---------+---------+
                                    |         |         |
                                    | gRPC    | gRPC    | gRPC
                                    v         v         v
+------------------------+  +-------+---+ +---+-------+ +---------+--+
|    registry-service    |  | mlops-service   | |  edge-connector-   |
| (Models/Scripts/Db)    |  | (Compilation)   | |      service       |
+-----------+------------+  +-------+---+ +---+-------+ +----+----+--+
            |                       |         |              |
            | MinIO / PG            | Docker  | MQTT         | Mongo / Prom
            v                       v         v              v
+-----------+------------+  +-------+---+ +---+-------+ +----+----+--+
| Storage & Databases    |  | Docker    | | MQTT      | | Metrics &  |
| (PostgreSQL & MinIO)   |  | Socket    | | Broker    | | Telemetry  |
+------------------------+  +-----------+ +-----------+ +------------+
                                               ^
                                               | MQTT (Commands, Telemetry)
                                               v
                                    +---------+---------+
                                    |     Device        |
                                    |   Edge Agent      |
                                    +-------------------+
```

### Key Components

* **Frontend (Next.js)**: A modern, intuitive dashboard interface for managing devices, uploading model/script artifacts, viewing live logs, and visualizing telemetry charts.
* **API Gateway (FastAPI)**: Centralizes frontend requests, handles JWT authentication, and exposes a clean REST API while routing internal traffic using gRPC.
* **Microservices (gRPC)**:
  * `registry-service`: Manages the database tables and metadata for devices, models, and scripts.
  * `mlops-service`: Orchestrates model compilation by interfacing with Docker sockets to isolate resource-intensive compiling tasks.
  * `edge-connector-service`: Handles communications with edge agents via MQTT, stores inference results in MongoDB, and exposes system telemetry for Prometheus.
* **Edge Runtime**: A Python agent optimized to run on the physical device, responsible for downloading models, verifying files with SHA-256 checksums, and executing inference tasks via the `aura_hw` library.

---

## Supported Hardware

AURA abstracts the complexity of the underlying hardware acceleration. Developers write generic inference scripts, and the platform handles the execution backend routing:

| Hardware Device | Supported Model Format | Support Status |
|---|---|---|
| **Raspberry Pi 5 + Hailo-8** | `.hef` (Hailo Executable Format) | Full (Production) |
| **Raspberry Pi 5 + Hailo-8L** | `.hef` | Full (Production) |
| **Raspberry Pi 5 + AI Camera (IMX500)** | `packerOut.zip` | Full (Production) |
| **Raspberry Pi 5 (CPU)** | `.onnx` | Full (Production) |
| **NVIDIA Jetson Orin Nano** | `.engine` (TensorRT) | Base Integration (Preliminary) |

To start deploying your own models, head over to the [Platform Execution Tutorial](tutorials/run_platform) to set up the system.
