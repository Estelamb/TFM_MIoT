# AURA Developer Guide

This guide is designed for developers who want to extend **AURA Platform** by adding new hardware compiler architectures, integrating custom sensor/actuator peripherals, or maintaining the platform's codebase.

---

## 1. Project Microservices Architecture

AURA is built on top of a modular architecture consisting of the following key services:
* **`api-gateway`**: FastAPI gateway exposing HTTP REST endpoints, verifying JWT auth, and routing to internal gRPC microservices.
* **`registry-service`**: gRPC service managing metadata storage (PostgreSQL via SQLAlchemy) and binary artifact registry (MinIO S3 integration).
* **`mlops-service`**: gRPC service running compile tasks asynchronously (interacting with local Docker daemon for containerized tasks).
* **`edge-connector-service`**: gRPC service handling active MQTT connections, ingesting telemetry, subscribing to inference metrics, and saving them to MongoDB and Prometheus.

---

## 2. Adding a New Hardware Architecture

The platform dynamically scans and registers hardware architectures placed in subdirectories under the project root-level `./hardware/hw_arch/` folder.

### Steps to Add an Architecture

1. **Copy the Template**:
   Copy the `./hardware/hw_arch/template` directory and name it after your target hardware architecture identifier (e.g., `./hardware/hw_arch/hailo10`).

2. **Implement your Compiler**:
   Inside your new folder, you will find two subdirectories:
   * `compilation/`: Contains compilation logic (`compiler.py` and any packaging pipelines).
   * `inference/`: Placeholder directory for future runtime inference code.

   Edit `compilation/compiler.py` and:
   * Define a global `LABEL` string variable at the top of the file specifying a friendly name (e.g. `LABEL = "Hailo-10"`).
   * Implement a subclass of `CompilerBase`:
     * Set class attributes:
       * `EXECUTION_STRATEGY`: `"docker"` or `"python"`.
       * `DOCKER_IMAGE`: The Docker tag required for docker-based compilation (empty for Python-based).
       * `OUTPUT_FORMAT`: The compiled file extension (e.g. `.hef`, `.bin`, `.zip`).
       * `SUPPORTED_HARDWARE`: A list of hardware types this compiler supports (e.g., `["hailo10"]`).
   * Implement the `async def compile()` method:
     1. Download the source model `.pt` file from the MinIO `models` bucket using the `source_key`.
     2. Perform compilation (invoke an external docker container or run custom python scripts).
     3. Upload output bytes to the MinIO `compiled` bucket using `upload_bytes()`.
     4. Return a `CompilationResult(success=True, compiled_key=..., compiled_sha256=...)` (or `success=False` with error message).

3. **Provide Pipeline Scripts (Optional)**:
   Add any helper files (like pipeline configurations, calibrations, splits) directly inside your architecture's `compilation/` folder.

4. **Environment / Dependencies**:
   * If Python-based: add the required python packages to `services/mlops-service/requirements.txt`.
   * If Docker-based: ensure the target Docker image is built/pulled on the host machine running the MLOps microservice.

5. **Deploy**:
   Rebuild and restart the services using:
   ```bash
   docker compose up -d --build mlops-service
   ```
   The gateway and frontend will automatically discover and display the new hardware option on the IoT Edge Devices registration page.

---

## 3. Execution Strategies

### Docker-Based
* Use `asyncio.create_subprocess_exec("docker", "run", ...)` to invoke compiler containers.
* Mount a shared folder under the temporary directory to transfer files into and out of the Docker container.
* Check return codes and log errors carefully.

### Python-Based
* Run CPU-intensive compiling logic in a separate worker thread using `await asyncio.to_thread(self._blocking_function, ...)`.
* Avoid blocking the asyncio event loop.

---

## 4. Adding a New Sensor or Actuator Peripheral

Peripherals are scanned dynamically at startup from the project root-level `./hardware/sensors/` and `./hardware/actuators/` directories, organized by category.

### Steps to Add a Peripheral

1. **Create Category and Peripheral Directories**:
   Under `./hardware/sensors/` or `./hardware/actuators/`, choose or create an appropriate category directory (e.g., `temperature/` or `led/`). Inside it, create your peripheral's directory named after its identifier (e.g., `dht22_temperature/`).
   
   Example directory path:
   `./hardware/sensors/temperature/dht22_temperature/library.py`

2. **Add a `library.py` File**:
   Create a `library.py` inside your new directory. This file should contain any drivers, setup code, or communication handlers for the peripheral, as well as a global module-level `LABEL` variable specifying the friendly name.
   
   Example `library.py` for a sensor:
   ```python
   LABEL = "DHT22 Temperature Sensor"

   class DHT22Library:
       def __init__(self, pin: int = 4):
           self.pin = pin

       def initialize(self) -> bool:
           return True

       def read_value(self) -> dict:
           return {"temperature_celsius": 24.5, "humidity_percent": 45.2}
   ```

3. **Deploy**:
   Rebuild and restart the services using:
   ```bash
   docker compose up -d --build mlops-service
   ```
   The gateway and frontend will automatically discover the component, load the friendly name from `LABEL` dynamically, and display it in the catalog page.

---

## 5. Compiling Documentation Locally

To build and verify documentation before pushing to GitHub Pages:

### Sphinx (Python Backend & Architecture Docs)
Navigate to the docs folder and install dependencies:
```bash
pip install -r docs/requirements.txt
```
Compile the HTML pages:
```bash
# On Linux/macOS
make -C docs/sphinx html

# On Windows (from root folder)
python -m sphinx.cmd.build -M html docs/sphinx/source docs/sphinx/build
```

### TypeDoc (TypeScript Frontend Docs)
Navigate to the frontend folder and build TS references:
```bash
cd frontend
npx typedoc --options ../docs/typedoc/typedoc.json
```
The output pages will be saved under `docs/typedoc/output`.
