# AURA Edge Runtime — Operator & Integrator Guide

This guide explains the steps required to run the AURA Edge Runtime on a device and outlines the procedures for adding support for new peripherals or hardware architectures.

---

## 1. Startup & Deployment Guide

The AURA Edge Runtime consists of two main components:
1. **Edge Agent (Docker)**: The core orchestrator that handles telemetry, the local inference loop, and receives OTA deployments from the central AURA platform.
2. **Hardware Daemon (Host)**: A lightweight HTTP service running natively on the host OS to expose physical hardware components (such as Picamera2 and Hailo accelerators) without requiring privileged flags or complex mounts in Docker.

### Prerequisites
* Docker and Docker Compose installed.
* Python 3.9 or higher (if running in physical mode with native host libraries).
* (For physical mode) Driver SDKs and kernel modules preinstalled on the host (e.g. `hailort`, `libcamera`).

### Step 1: Configure the Environment (.env)
Copy the example environment file and edit its keys:
```bash
cp .env.example .env
```

Key environment variables:
* `AURA_DEVICE_ID`: Unique identifier for the device (e.g., `IoT-Edge-Device-01`).
* `AURA_MQTT_HOST`: IP/Host of the AURA MQTT broker (e.g., `172.18.0.1` or a cloud address).
* `AURA_HARDWARE_TYPE`: Hardware accelerator type. Supported values: `simulated`, `rpi`, `rpi_ai_cam`, `hailo8`, `hailo8l`, `jetson_orin_nano`.
* `AURA_PERIPHERALS`: Comma-separated list or JSON array of enabled peripherals (e.g., `camera_0,gps_0`).
* `AURA_COORDINATES`: Initial deployment coordinates (e.g., `[-3.7038, 40.4168]`).

### Step 2: Start the Runtime

#### Option A: Running in Simulated Mode (Development/Testing)
No physical hardware is required. All devices (including cameras and GPS) are simulated.
Simply run the startup script, which configures networks and launches the containers:
* **Linux/macOS**:
  ```bash
  chmod +x run_edge.sh
  ./run_edge.sh
  ```
* **Windows (PowerShell)**:
  ```powershell
  ./run_edge.ps1
  ```

#### Option B: Running in Physical Mode (Production/Real Hardware)
1. **Start the Hardware Daemon on the Host**:
   Install dependencies and start the daemon natively on the host OS:
   ```bash
   pip install -r requirements.txt
   python hardware_daemon.py
   ```
   *Note: The daemon listens locally on http://localhost:8008.*

2. **Start the Edge Agent in Docker**:
   Run the startup script to launch the containerized orchestrator:
   ```bash
   ./run_edge.sh
   ```

---

## 2. How to Add a New Peripheral (Sensor/Actuator)

To add support for a new physical sensor, actuator, or device:

### Step A: Create the Driver Folder
Create the directory structure inside `hardware/` based on its category (`sensors`, `actuators`, or `others`):
```
hardware/
├── sensors/
│   └── <sensor_type>/              # E.g., "temperature" or "gps"
│       ├── library.py               # Category-level generic wrapper
│       └── <driver_name>/           # E.g., "bme280" or "gps_simulated"
│           └── library.py           # Specific driver implementation
```

### Step B: Implement the Driver Class
The specific driver file (`hardware/sensors/<sensor_type>/<driver_name>/library.py`) must define a friendly label and the driver class:
```python
class MyCustomSensor:
    LABEL = "My Custom Physical Sensor"

    def __init__(self, **kwargs):
        # Initialize physical bus connections (e.g., I2C, SPI, or GPIO pins)
        self.pin = kwargs.get("pin", 4)

    def initialize(self) -> bool:
        # Startup and configuration logic for the chip/sensor
        return True

    def read_value(self) -> float:
        # Return the measured value (e.g., temperature, distance)
        return 23.5

    def close(self) -> None:
        # Cleanup connections and resources
        pass
```

### Step C: Register & Activate
1. Register the new device type in [device_manager.py](file:///c:/Users/Estela/TFM_MIoT/edge-runtime/aura_hw/device_manager.py) under `_TYPE_FACTORIES`:
   ```python
   def _make_custom_sensor(cid: str, driver: str) -> DeviceBackend:
       from aura_hw.backends.devices.sensor.general import GeneralSensorBackend
       return GeneralSensorBackend(cid, "custom_sensor", driver)
   ```
2. Add the component to [components_config.yaml](file:///c:/Users/Estela/TFM_MIoT/edge-runtime/config/components_config.yaml):
   ```yaml
   - id: custom_sensor_0
     type: custom_sensor
     driver: my_physical_driver
     enabled: true
     params:
       pin: 12
   ```

---

## 3. How to Add a New Hardware Architecture (AI Accelerator)

To integrate support for a new compilation and deep learning inference chip (e.g., *Google Coral Edge TPU*, *Intel Myriad*):

### Step A: Register the Compiler
1. Add the compiler directory to `hardware/hw_arch/<arch_name>/compilation/compiler.py`.
2. Inherit from MLOps' `CompilerBase` and override metadata constants (e.g., `LABEL`, `OUTPUT_FORMAT`) and the async `compile()` method.

### Step B: Register the Inference Driver
Create the inference wrapper under `hardware/hw_arch/<arch_name>/inference/library.py` implementing weights loading and model execution routines.

### Step C: Integrate into the Host Hardware Daemon
If the new accelerator requires native host-level libraries:
1. **Create the Manager**:
   Create a python file in `edge-runtime/daemon/<arch_name>.py` (e.g. `edge-runtime/daemon/coral.py`):
   ```python
   from daemon.shared import logger

   class CoralManager:
       def __init__(self):
           self.engine = None

       def load(self, model_bytes: bytes) -> dict:
           # Native model loading logic
           return {"status": "success"}

       def infer(self, frame_bytes: bytes) -> dict:
           # Native inference execution
           return {"status": "success", "detections": []}

       def unload(self) -> None:
           self.engine = None

   coral_manager = CoralManager()
   ```
2. **Automatic Detection**:
   The daemon package automatically scans the `daemon/` folder and exposes any variables ending in `_manager`, so your new singleton `coral_manager` is imported and registered dynamically at startup.
3. **Map Endpoints**:
   Update the `/load`, `/infer`, and `/unload` handlers in [hardware_daemon.py](file:///c:/Users/Estela/TFM_MIoT/edge-runtime/hardware_daemon.py) to forward requests to your new manager when `HARDWARE_TYPE` matches `<arch_name>`.
