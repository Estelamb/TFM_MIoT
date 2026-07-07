# How to Add New Hardware to the AURA Platform

The AURA Platform is designed with a plug-and-play architecture for custom hardware integration. You can add new target platforms in two ways:
1. **Hardware Architectures (`hardware/hw_arch`)**: Define how to compile and how to inference generic `.pt` model files into hardware-specific binary targets.
2. **Peripheral Drivers (`hardware/sensors`, `hardware/actuators`, `hardware/others`)**: Define how to control and fetch metrics from connected sensors or write signals to actuators.

---

## 1. Adding a Hardware Architecture Compiler

Model compilation is scanned dynamically by the `mlops-service` from the subdirectories inside `hardware/hw_arch`.

### Step 1: Create the Compiler Module
Create a new directory structure:
```bash
hardware/hw_arch/<your_hw_arch_name>/compilation/
```
Under this directory, create `compiler.py` and declare a subclass of `CompilerBase`:

```python
from app.compilers.base import CompilerBase, CompilationResult

LABEL = "My Hardware Architecture"  # Friendly name displayed in the Web UI

class MyHWArchCompiler(CompilerBase):
    EXECUTION_STRATEGY = "docker"                    # Either "docker" or "python"
    DOCKER_IMAGE = "my-hw-arch-sdk-image:latest"         # Required if strategy is "docker"
    OUTPUT_FORMAT = ".hef"                           # Resulting extension
    SUPPORTED_HARDWARE = ["my_hw_arch_v1", "my_hw_arch_v2"]  # Internal identifier tags
```

### Step 2: Implement the `compile()` Method
Every compiler must implement `async def compile(...)`. The method is responsible for:
1. Downloading the raw `.pt` PyTorch model weights from MinIO.
2. Running the hardware compiler utility (e.g., executing compilation inside a Docker container via `run_subprocess_with_logs`).
3. Uploading the compiled binary to the `compiled` MinIO bucket.
4. Returning a `CompilationResult`.

#### Example Implementation
```python
import os
import tempfile
from app.compilers.base import CompilerBase, CompilationResult
from shared.utils.minio import get_minio, upload_bytes

class MyNPUCompiler(CompilerBase):
    # ... metadata fields ...

    async def compile(
        self,
        model_id: str,
        source_key: str,
        num_classes: int,
        class_names: list[str],
        hardware_type: str,
        dataset_id: str,
        dataset_key: str,
        base_architecture: str = "",
        input_size: str = "",
    ) -> CompilationResult:
        minio = get_minio()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. Download source PyTorch model
            pt_path = os.path.join(tmpdir, "model.pt")
            await self.log_progress(model_id, "Downloading source model weights...")
            await minio.fget_object(self._bucket_models, source_key, pt_path)
            
            # 2. Run NPU toolchain compiler (using helper log stream)
            output_bin_path = os.path.join(tmpdir, "model.hef")
            cmd = ["npu-compiler", "--input", pt_path, "--output", output_bin_path]
            
            await self.log_progress(model_id, "Running NPU compilation...")
            rc = await self.run_subprocess_with_logs(model_id, cmd, cwd=tmpdir)
            if rc != 0:
                return CompilationResult(success=False, error="Compilation process failed.")
                
            # 3. Upload compiled artifact
            dest_key = f"{model_id}/model{self.OUTPUT_FORMAT}"
            await self.log_progress(model_id, "Uploading compiled artifact...")
            with open(output_bin_path, "rb") as f:
                sha256 = await upload_bytes(self._bucket_compiled, dest_key, f.read())
                
            return CompilationResult(
                success=True,
                compiled_key=dest_key,
                compiled_sha256=sha256
            )
```

---

## 2. Adding Sensor and Actuator Drivers

AURA dynamically scans connected peripherals so they can be monitored and managed by the Edge Runtime agent.

### Directory Convention
Peripherals must follow this directory pattern:
* **Sensors**: `hardware/sensors/<device_type>/<driver_name>/library.py`
* **Actuators**: `hardware/actuators/<device_type>/<driver_name>/library.py`
* **Others**: `hardware/others/<device_type>/<driver_name>/library.py`

Where:
* `<device_type>` is the type/category classification of the peripheral (e.g., `camera`, `gps`, `temperature`).
* `<driver_name>` is the name of the specific driver implementation (e.g., `imx500`, `bme280`, `gps_simulated`).

### Step 1: Create `library.py`
Define a class in `library.py` representing your peripheral device. It must define a module-level variable `LABEL`.

```python
# hardware/sensors/temperature/bme280/library.py
import logging

logger = logging.getLogger(__name__)

LABEL = "BME280 Temperature & Humidity Sensor"

class BME280Driver:
    def __init__(self, i2c_address=0x76, **kwargs):
        self.address = i2c_address
        self.sensor = None

    def initialize(self) -> bool:
        try:
            # Import hardware packages inside initialize/methods so it does not crash on non-Pi platforms
            import smbus2
            import bme280
            self.port = smbus2.SMBus(1)
            self.sensor = bme280
            return True
        except ImportError:
            logger.warning("BME280 libraries not found. Falling back to Mock simulation.")
            return self.initialize_mock()

    def initialize_mock(self) -> bool:
        self.is_mock = True
        return True

    def read_value(self) -> dict:
        if getattr(self, "is_mock", False):
            import random
            return {"temperature": random.uniform(20.0, 25.0), "humidity": random.uniform(40.0, 50.0)}
            
        data = self.sensor.sample(self.port, self.address)
        return {"temperature": data.temperature, "humidity": data.humidity}

    def close(self):
        if hasattr(self, "port"):
            self.port.close()
```

### Step 2: Graceful Mock Fallback
Since developers test the platform on different OS environments, drivers must not crash when native system dependencies are missing (e.g. SMBus packages on a standard dev laptop). Always implement a fallback to a simulated/mock driver in case of `ImportError`.

---

## 3. Integrating with the Hardware Daemon

When running the Edge Agent inside a Docker container, accessing native host hardware resources (such as cameras and hardware accelerators like Hailo-8 or IMX500) can be complex and typically requires privileged container flags or complex device mounts.

AURA solves this by running a lightweight host-level **Hardware Daemon** (`hardware_daemon.py`). The daemon runs directly on the host operating system, interfaces with native drivers (e.g. `picamera2`), and exposes a local HTTP API for the containerized Edge Agent.

The standard daemon API includes:
* `GET /capture`: Returns the latest camera frame as raw image bytes.
* `GET /status`: Returns a JSON object with system capability details.
* `POST /load`: Accepts model bytes (such as a compiled HEF) and initializes the hardware context.
* `POST /infer`: Performs inference on input RGB bytes and returns model outputs.
* `POST /unload`: Cleans up the hardware context.

### Extending the Daemon for New Accelerators

If you are adding a new hardware accelerator that cannot be accessed directly from inside Docker, you should extend the Hardware Daemon:

1. **Create a manager module** under `edge-runtime/daemon/<your_accelerator>.py`.
2. **Implement your manager class** and instantiate a global singleton instance ending in `_manager` (for example, `my_accel_manager = MyAcceleratorManager()`). The daemon's `__init__.py` will automatically scan and export it.
3. **Update the HTTP Router** in `hardware_daemon.py` to forward requests from `/load` or `/infer` to your manager based on the active `AURA_HARDWARE_TYPE` environment variable.

---

## 4. Registering components config

When running on an edge device, the active driver and parameters are configured in the `components_config.yaml` file located in the configuration directory of the agent. The PAL wrapper reads the current layout and dynamically resolves and runs the specified drivers.
