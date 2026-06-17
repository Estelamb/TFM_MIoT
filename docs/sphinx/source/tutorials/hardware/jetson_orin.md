# Tutorial: NVIDIA Jetson Orin Nano

*(This tutorial will be completed by the user. Placeholder reserved for the integration guide of NVIDIA Jetson Orin Nano using TensorRT).*

## Introduction to NVIDIA Jetson Orin Nano

NVIDIA Jetson Orin Nano features an NVIDIA Ampere architecture GPU and deep learning accelerators delivering up to 40 TOPS of AI performance. It runs complex models optimized in TensorRT (`.engine` format).

## Hardware and OS Setup

* NVIDIA Jetson Orin Nano Developer Kit.
* MicroSD card or NVMe SSD with **JetPack 6.0** or higher installed.
* Python 3.10+ and the `tensorrt` Python package.

## Detection and Configuration

AURA detects the platform by reading `/etc/nv_tegra_release`.

To force the backend manually, configure:
```bash
AURA_HARDWARE_TYPE=jetson_orin_nano
```

Write in this section the detailed guides to compile and deploy TensorRT `.engine` models from the AURA backend.
