# How to Add New Hardware to the AURA Platform

The AURA Platform is designed with a plug-and-play architecture for custom hardware integration. You can add new target platforms in two ways:
1. **Hardware Compilers (`hardware/hw_arch`)**: Define how to compile generic `.pt` model files into hardware-specific binary targets.
2. **Peripheral Drivers (`hardware/sensors`, `hardware/actuators`)**: Define how to control and fetch metrics from connected sensors or write signals to actuators.

---

## 1. Adding a Hardware Compiler

Model compilation is scanned dynamically by the `mlops-service` from the subdirectories inside [hardware/hw_arch/](file:///c:/Users/Estela/TFM_MIoT/hardware/hw_arch).

### Step 1: Create the Compiler Module
Create a new directory structure:
```bash
hardware/hw_arch/<your_npu_name>/compilation/
```
Under this directory, create `compiler.py` and declare a subclass of `CompilerBase`:

```python
from app.compilers.base import CompilerBase, CompilationResult

LABEL = "My NPU Accelerator"  # Friendly name displayed in the Web UI

class MyNPUCompiler(CompilerBase):
    EXECUTION_STRATEGY = "docker"                    # Either "docker" or "python"
    DOCKER_IMAGE = "my-npu-sdk-image:latest"         # Required if strategy is "docker"
    OUTPUT_FORMAT = ".hef"                           # Resulting extension
    SUPPORTED_HARDWARE = ["my_npu_v1", "my_npu_v2"]  # Internal identifier tags
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
* **Sensors**: `hardware/sensors/<category>/<peripheral_name>/library.py`
* **Actuators**: `hardware/actuators/<category>/<peripheral_name>/library.py`
* **Others**: `hardware/others/<category>/<peripheral_name>/library.py`

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

## 3. Registering components config

When running on an edge device, the active driver and parameters are configured in the `components_config.yaml` file located in the configuration directory of the agent. The PAL wrapper reads the current layout and dynamically resolves and runs the specified drivers.
