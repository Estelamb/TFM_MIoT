# Overview

AURA is an end-to-end platform for deploying computer vision models
to IoT edge devices. It covers the full lifecycle:

1. **Upload** a trained `.pt` model
2. **Compile** it for your target hardware (Hailo-8, IMX500, TFLite, TensorRT)
3. **Deploy** model + inference script to one or more edge devices over MQTT
4. **Monitor** CPU/RAM telemetry and inference results in real time

## Key design decisions

- **gRPC** for all internal service-to-service communication
- **MQTT** as the cloud-to-edge transport (anonymous in PoC, pluggable via `shared/transport`)
- **SHA-256 verification** on every model and script download at the edge
- **Hardware abstraction** via `aura_hw` — inference scripts are hardware-agnostic

## Supported hardware

| Device | Model format | Status |
|---|---|---|
| RPi5 + Hailo-8 | `.hef` | ✅ Full |
| RPi5 + Hailo-8L | `.hef` | ✅ Full |
| RPi5 + AI Camera (IMX500) | `packerOut.zip` | ✅ Full |
| RPi5 (CPU) | `.tflite` | ⚠️ Backend ready, compiler stub |
| Jetson Orin Nano | `.engine` | ⚠️ Stub |
