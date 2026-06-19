# Tutorial: Raspberry Pi 5 (CPU - ONNX)

*(This tutorial will be completed by the user. Placeholder reserved for the CPU execution guide on Raspberry Pi using ONNX Runtime).*

## Introduction to CPU Inference

When no hardware accelerator (NPU/TPU) is available on the edge device, AURA can process models on the host CPU using ONNX (`.onnx` format). Performance will be lower, but it is ideal for debugging and lightweight models.

## Software Requirements

* Python 3.10+ installed on the Raspberry Pi.
* ONNX Runtime library:
  ```bash
  pip install onnxruntime
  ```

## Using the CPU Backend in AURA

The `aura_hw` runtime automatically falls back to CPU when no accelerators are detected. To force it manually, set:

```bash
AURA_HARDWARE_TYPE=rpi
```

Add your specific notes and benchmarks in this section.
