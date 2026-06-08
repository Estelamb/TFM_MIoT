"""
Camera device backends for AURA HAL.

Available backends
------------------
OpenCVCameraBackend
    Generic USB / CSI / RTSP camera via OpenCV. Works on any platform.
LibcameraBackend
    Raspberry Pi native camera stack via libcamera (no picamera2 needed).
IMX500CameraBackend
    Sony IMX500 AI Camera via picamera2 (frame capture only — inference
    is handled by the separate RPiAICamBackend in backends/inference/).
"""
from aura_hw.backends.devices.camera.base import CameraBackend
from aura_hw.backends.devices.camera.opencv import OpenCVCameraBackend
from aura_hw.backends.devices.camera.libcamera import LibcameraBackend
from aura_hw.backends.devices.camera.imx500 import IMX500CameraBackend

__all__ = [
    "CameraBackend",
    "OpenCVCameraBackend",
    "LibcameraBackend",
    "IMX500CameraBackend",
]
