# Tutorial: Raspberry Pi 5 + Hailo-8

*(This tutorial will be completed by the user. Placeholder reserved for the integration guide of Raspberry Pi 5 with the Hailo-8 module).*

## Introduction to Hailo-8 Hardware

The Hailo-8 Deep Learning Processor (NPU) delivers up to 26 TOPS of compute power for AI tasks at the edge. Describe here how it connects and behaves within the AURA platform.

## Hardware Requirements and Connection

* Raspberry Pi 5 with a suitable power supply.
* PCIe Shield (e.g., Pineberry Pi HAT, official Raspberry Pi HAT, or other manufacturers).
* Hailo-8 M.2 Key M module.
* Heat sink and active cooling fan (highly recommended).

## OS Configuration and Drivers

Step-by-step instructions to enable PCIe and detect the NPU:

1. Modify `/boot/firmware/config.txt`:
   ```ini
   dtparam=pciex1
   # Enable Gen 3 speed if supported
   dtparam=pciex1_gen=3
   ```
2. Install the kernel driver and the `hailortcli` tool:
   ```bash
   # Commands to install firmware and dkms...
   ```
3. Check hardware detection:
   ```bash
   hailortcli fw-control identify
   ```

## Model Compilation for Hailo-8

Steps to compile models using the AURA MLOps service or locally using the Hailo Software Suite (DFG) to generate `.hef` files.

## Inference Script Example in AURA

Example script for Hailo-8:

```python
# Place here your custom inference Python code adapted for Hailo-8
```
