# Edge Runtime

## Running the Edge Agent on a Physical Device

The edge agent runs on the target physical hardware (e.g., Raspberry Pi 5). It connects to the AURA Platform via MQTT to receive deployment commands and report device telemetry.

### 1. Copy runtime files to the edge device
Transfer the `edge-runtime/` folder from the project to the local storage of your edge device (using `scp`, `rsync`, or cloning the repository directly on the device).

### 2. Install dependencies on the device
The edge agent requires Python 3.10 or higher. Navigate to the runtime folder and install dependencies:

```bash
# Navigate to the runtime folder
cd edge-runtime

# Install required Python packages
pip install -r requirements.txt
```

* **Important**: If you plan to use accelerators such as the Hailo-8, make sure that the hardware vendor SDK and kernel drivers (e.g., HailoRT) are installed on the device operating system before starting the agent.

### 3. Configure the Environment Variables
Before starting the agent, copy the template `.env.example` to `.env` in the `edge-runtime/` directory:

```bash
cp .env.example .env
```

Open the `.env` file and customize the connection and identifier settings as needed (e.g. `AURA_DEVICE_ID`, `AURA_MQTT_HOST`, `AURA_HARDWARE_TYPE`, etc.).

### 4. Run the Edge Runtime Stack
The Edge Runtime is composed of a host-level Hardware Daemon and the containerized Edge Agent. You can automatically build, launch, and run both components using the provided startup scripts:

* **On Linux / macOS**:
  ```bash
  chmod +x run_edge.sh
  ./run_edge.sh
  ```

* **On Windows (PowerShell)**:
  ```powershell
  .\run_edge.ps1
  ```

### Agent Configuration Parameters

| Variable | Default Value | Description |
|---|---|---|
| `AURA_DEVICE_ID` | `dev-device-001` | Unique device identifier. Must exactly match the Device ID registered in the AURA web console. |
| `AURA_MQTT_HOST` | `localhost` | IP address or domain name where the platform's MQTT broker is running. |
| `AURA_MQTT_PORT` | `1883` | MQTT broker port (usually `1883`). |
| `AURA_HARDWARE_TYPE` | *Auto-detected* | Overrides automatic hardware detection. Valid values: `hailo8`, `hailo8l`, `imx500`, `rpi` (CPU). |
| `AURA_TELEMETRY_INTERVAL` | `10` | Frequency in seconds at which the agent sends CPU/RAM telemetry messages. |

The scripts will establish the connection with the broker. Upon success, the device state will change to **Online** in the AURA web dashboard.

---

## Next Steps

Now that your Edge Runtime is running and connected, you can start writing and deploying custom models and logic:
* Learn how to write custom inference code that targets the edge sensors in the [How to Create a Custom Inference Script](create_script.md) tutorial.
* If you want to integrate new NPU accelerators or custom hardware sensors into the platform, follow the [How to Add New Hardware](add_hardware.md) guide.