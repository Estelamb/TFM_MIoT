# How to Use the Interface and Deploy Models in AURA

This section explains how to interact with the AURA Web Management Console to register devices, upload ML artifacts (models and scripts), and execute Over-the-Air (OTA) deployments.

---

## Demo Mode

If you wish to explore the interface without running the backend microservices or configuring a physical edge device, the frontend includes a **Demo Mode**:

* Locate the **Demo Mode** toggle switch in the bottom-right corner of the sidebar menu.
* When toggled on, the Next.js app loads static mock datasets for devices, real-time metrics, and deployment pipelines, allowing you to explore the pages immediately.
* When toggled off (Real Mode), the cache is cleared and the frontend attempts to call your local `api-gateway` on port `8000` via HTTP REST and WebSockets.

---

## Workspace Flow in Real Mode

To deploy a vision model to a physical edge device, follow these steps in order:

### Step 1: Register a Device

1. Open the sidebar and navigate to the **Devices** section.
2. Click the **Register Device** button.
3. Fill in the required parameters:
   * **Device ID**: The unique identifier of your hardware (e.g., `my-raspberry-01`). This must exactly match the `AURA_DEVICE_ID` environment variable of the edge agent.
   * **Name**: A user-friendly name to identify the device in the dashboard.
   * **Location**: The physical location of the device (optional).
   * **Hardware Type**: Select the target hardware acceleration available on the device (Hailo-8, AI Camera IMX500, CPU, etc.).
4. Save the registration. The device status will remain **Offline** until the agent starts running on the device with this matching ID.

### Step 2: Upload a Machine Learning Model

1. Go to the **Models** section in the sidebar.
2. Click the **Upload Model** button.
3. Fill in the form:
   * **Name**: A descriptive name for the model (e.g., `yolov8n-detect`).
   * **Version**: Version tag (e.g., `1.0.0`).
   * **Target Hardware**: The target hardware this model is optimized for or will be compiled against.
   * **Model File**: Choose your local model weights file (e.g., a PyTorch `.pt` file).
4. Click **Submit**. The file will be uploaded to the MinIO S3 `models` bucket and logged in the database.

### Step 3: Upload an Inference Script

Inference scripts define the input preprocessing, model execution, and output postprocessing on the edge agent.

1. Navigate to the **Scripts** section.
2. Click the **Upload Script** button.
3. Complete the form:
   * **Name**: A unique name (e.g., `yolo-detection-script`).
   * **Version**: The version tag of the script.
   * **File**: Upload your Python script file (`.py`). The script must follow the agent execution API.

#### Example of an Inference Script
```python
from aura_hw import execute_inference
import numpy as np

def pre_inference(raw_input):
    # Transform raw input image to a NumPy tensor
    # Basic pre-processing logic...
    return raw_input

def post_inference(raw_output):
    # Format raw tensor outputs to structured JSON
    return [{"class": "person", "confidence": 0.89, "bbox": [100, 50, 250, 300]}]

def run(raw_input):
    # Main function periodically invoked by the AURA agent runtime
    processed_input = pre_inference(raw_input)
    raw_output = execute_inference(processed_input)
    return post_inference(raw_output)
```

### Step 4: Create and Launch a Deployment

Once your device is online, and both a model and an inference script have been uploaded, you can link them in a **Deployment**:

1. Go to the **Deployments** section in the sidebar.
2. Click the **New Deployment** button.
3. Select your **Device** from the dropdown.
4. Select the **Model** and **Script** you wish to run on that device.
5. Click **Deploy**.

#### Under-the-Hood Workflow:
1. The `api-gateway` receives the request and forwards it to the `edge-connector-service`.
2. The connector service publishes a JSON command on the MQTT topic: `device/{id}/commands`.
3. The local edge agent receives the command, downloads the model and script files directly from MinIO using secure pre-signed URLs, checks the SHA-256 hashes, loads the new runtime in-memory, and starts executing the inference loop.
4. The agent publishes a confirmation event on the topic `device/{id}/events` containing the acknowledgment.

### Step 5: Real-Time Telemetry and Monitoring

1. Open the **Monitoring** section or click on the device name in the devices list.
2. The dashboard displays real-time updates via WebSockets:
   * **Resource Charts**: Graphical charts showing active CPU percentage, RAM consumption, and network usage.
   * **Runtime State**: The name and version of the model and script currently running on the device.
   * **Inference Live Stream**: The raw JSON output payload sent by the agent on the MQTT inference channel (`device/{id}/inference`).
