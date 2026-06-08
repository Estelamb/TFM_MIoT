# Adding a New Hardware Architecture

The platform automatically detects hardware architectures placed in subdirectories under the project root-level `./hardware/hw_arch/` directory.

## Steps

1. **Copy the Template**:
   Copy the `./hardware/hw_arch/template` directory and name it after your target architecture/hardware identifier (e.g., `./hardware/hw_arch/hailo10`).

2. **Implement your Compiler**:
   Inside your new folder, you will find two subdirectories:
   * `compilation/`: Contains compilation logic (`compiler.py` and any packaging pipelines).
   * `inference/`: Placeholder directory for future runtime inference code.

   Edit `compilation/compiler.py` and:
   - Define a global `LABEL` string variable at the top of the file specifying a friendly name (e.g. `LABEL = "Hailo-10"`).
   - Implement a subclass of `CompilerBase`:
     - Set class attributes:
       - `EXECUTION_STRATEGY`: `"docker"` or `"python"`.
       - `DOCKER_IMAGE`: The Docker tag required for docker-based compilation (empty for Python-based).
       - `OUTPUT_FORMAT`: The compiled file extension (e.g. `.hef`, `.bin`, `.zip`).
       - `SUPPORTED_HARDWARE`: A list of hardware types this compiler supports (e.g., `["hailo10"]`).
   - Implement `async def compile()`:
     a. Download source model `.pt` file from MinIO bucket `models` using `source_key`.
     b. Perform compilation (invoke external docker container or run python scripts).
     c. Upload output bytes to MinIO bucket `compiled` using `upload_bytes()`.
     d. Return `CompilationResult(success=True, compiled_key=..., compiled_sha256=...)` (or `success=False` with error message).

3. **Provide Pipeline Scripts (Optional)**:
   Add any helper files (like pipeline configurations, calibrations, splits) directly inside your architecture's `compilation/` folder.

4. **Environment / Dependencies**:
   - If Python-based: add required python dependencies to `services/compilation-service/requirements.txt`.
   - If Docker-based: add the Docker image to host runner, and set it as an env variable or default in `compiler.py`.

5. **Deploy**:
   Rebuild and restart the services using `docker compose up -d --build compilation-service`.
   The gateway and frontend will automatically discover and display the new hardware option on the IoT Edge Devices registration page.

---

## Execution Strategies

### Docker-Based
- Use `asyncio.create_subprocess_exec("docker", "run", ...)` to invoke compilers.
- Mount a shared folder under the temporary directory to transfer files into and out of Docker.
- Check return codes and log errors carefully.

### Python-Based
- Run CPU-intensive compiling logic in a separate worker thread using `await asyncio.to_thread(self._blocking_function, ...)`.
- Avoid blocking the asyncio event loop.

---

## Adding a New Sensor or Actuator Peripheral

Peripherals are scanned dynamically at startup from the project root-level `./hardware/sensors/` and `./hardware/actuators/` directories, organized by category.

### Steps

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
   Rebuild and restart the services using `docker compose up -d --build mlops-worker-service`.
   The gateway and frontend will automatically discover the component, load the friendly name from `LABEL` dynamically, and display it in the catalog page.

