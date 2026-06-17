# Tutorial: Raspberry Pi 5 (CPU - TFLite)

*(This tutorial will be completed by the user. Placeholder reserved for the CPU execution guide on Raspberry Pi using TensorFlow Lite).*

## Introduction to CPU Inference

When no hardware accelerator (NPU/TPU) is available on the edge device, AURA can process models on the host CPU using TensorFlow Lite (`.tflite` format). Performance will be lower, but it is ideal for debugging and lightweight models.

## Software Requirements

* Python 3.10+ installed on the Raspberry Pi.
* TensorFlow Lite Runtime library:
  ```bash
  pip install tflite-runtime
  ```

## Using the CPU Backend in AURA

The `aura_hw` runtime automatically falls back to CPU when no accelerators are detected. To force it manually, set:

```bash
AURA_HARDWARE_TYPE=rpi
```

Add your specific notes and benchmarks in this section.
