"""
Abstract base class for all AURA camera backends.

A camera backend manages a single image sensor: it opens the device,
captures frames as ``numpy.ndarray`` (BGR, HWC), and reports its state.

Concrete subclasses
-------------------
* :class:`~aura_hw.backends.devices.camera.opencv.OpenCVCameraBackend`
* :class:`~aura_hw.backends.devices.camera.libcamera.LibcameraBackend`
* :class:`~aura_hw.backends.devices.camera.imx500.IMX500CameraBackend`
"""
from __future__ import annotations

from abc import abstractmethod
from typing import Any

import numpy as np

from aura_hw.backends.devices.base import DeviceBackend


class CameraBackend(DeviceBackend):
    """Specialised device backend for image sensors.

    Adds the :meth:`capture_frame` method on top of the base
    :meth:`~aura_hw.backends.devices.base.DeviceBackend.read` interface
    so that callers have a typed, semantically clear API.
    """

    @property
    def device_type(self) -> str:
        return "camera"

    @abstractmethod
    def capture_frame(self) -> np.ndarray:
        """Capture and return the latest image frame.

        Returns:
            A ``numpy.ndarray`` with shape ``(H, W, 3)`` in BGR uint8.

        Raises:
            RuntimeError: If the camera has not been opened yet.
            IOError: If frame capture fails.
        """
        ...

    def read(self) -> Any:
        """Alias for :meth:`capture_frame` — satisfies the :class:`DeviceBackend` contract."""
        return self.capture_frame()
