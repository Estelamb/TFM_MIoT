# Edge Runtime

## Running the agent

```bash
AURA_DEVICE_ID=my-device-001 \
AURA_MQTT_HOST=<platform-ip> \
AURA_HARDWARE_TYPE=hailo8 \
python agent.py
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `AURA_DEVICE_ID` | `dev-device-001` | Must match the ID registered in the platform |
| `AURA_MQTT_HOST` | `localhost` | Platform MQTT broker hostname |
| `AURA_MQTT_PORT` | `1883` | MQTT port |
| `AURA_HARDWARE_TYPE` | auto-detect | Override hardware detection |
| `AURA_TELEMETRY_INTERVAL` | `10` | Seconds between telemetry publishes |

## Writing an inference script

```python
from aura_hw import execute_inference
import numpy as np

def pre_inference(raw_input):
    # preprocess → numpy tensor
    return tensor

def post_inference(raw_output):
    # postprocess → list of dicts
    return [{"class": "person", "confidence": 0.92, "bbox": [...]}]

def run(raw_input):   # called by the runtime
    return post_inference(execute_inference(pre_inference(raw_input)))
```

`execute_inference()` automatically routes to the correct hardware backend.

## Hardware detection order

1. `AURA_HARDWARE_TYPE` env var (override)
2. `hailortcli fw-control identify` → `hailo8` / `hailo8l`
3. `/etc/nv_tegra_release` → `jetson_orin_nano`
4. `libcamera-hello --list-cameras` with imx500 → `rpi_ai_cam`
5. `/proc/device-tree/model` with "raspberry" → `rpi`
6. Fallback → TFLite CPU
