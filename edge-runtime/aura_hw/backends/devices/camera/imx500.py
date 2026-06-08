"""
IMX500 Camera Backend
======================
Sony IMX500 AI Camera device backend — **frame capture only**.

The IMX500 is used both as a regular image sensor and as an on-sensor
AI accelerator.  This backend manages the *camera* role (frame capture,
resolution, fps).  The *inference* role (loading a model, retrieving
detection outputs) is managed separately by
:class:`~aura_hw.backends.inference.rpi_ai_cam.RPiAICamBackend`.

Requires: ``picamera2`` with IMX500 support (RPi OS Bookworm + raspi-firmware)

Configuration example in ``components_config.yaml``
----------------------------------------------------
::

    - id: camera_0
      type: camera
      driver: imx500
      enabled: true
      params:
        resolution: [640, 480]
        fps: 10
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

from aura_hw.backends.devices.camera.base import CameraBackend

logger = logging.getLogger(__name__)


class IMX500CameraBackend(CameraBackend):
    """Sony IMX500 AI Camera — frame capture device backend.

    Opens the IMX500 via ``picamera2`` for raw image capture without
    loading an inference model.  Useful when frame capture and inference
    need to be managed independently.

    Parameters
    ----------
    component_id:
        Unique component identifier from ``components_config.yaml``.
    """

    def __init__(self, component_id: str) -> None:
        super().__init__(component_id)
        self._camera = None
        self._imx500 = None
        self._params: dict = {}

    # ── DeviceBackend interface ──────────────────────────────────────────────

    @property
    def driver(self) -> str:
        return "imx500"

    def open(self, params: dict) -> None:
        """Initialise the IMX500 camera for frame capture.

        Args:
            params: Configuration dict with keys:

                * ``resolution`` (list[int]): ``[width, height]``.
                * ``fps`` (int): Target frame rate.
        """
        from picamera2 import Picamera2  # type: ignore[import]
        from picamera2.devices.imx500 import IMX500  # type: ignore[import]

        self._params = params
        resolution = params.get("resolution", [640, 480])
        fps = params.get("fps", 10)

        # Instantiate IMX500 without a model to use it as a plain camera
        self._imx500 = IMX500()
        self._camera = Picamera2(self._imx500.camera_num)
        config = self._camera.create_video_configuration(
            main={"size": tuple(resolution), "format": "BGR888"},
            controls={"FrameRate": fps},
        )
        self._camera.configure(config)
        self._camera.start()
        logger.info(
            f"[{self._component_id}] IMX500 camera opened: "
            f"camera_num={self._imx500.camera_num} res={resolution} fps={fps}"
        )

    def close(self) -> None:
        """Stop and release the IMX500 camera."""
        if self._camera is not None:
            self._camera.stop()
            self._camera = None
        self._imx500 = None
        logger.info(f"[{self._component_id}] IMX500 camera closed")

    def capture_frame(self) -> np.ndarray:
        """Capture the latest frame from the IMX500 sensor.

        Returns:
            BGR ``numpy.ndarray`` of shape ``(H, W, 3)``.

        Raises:
            RuntimeError: If the camera has not been opened.
        """
        if self._camera is None:
            raise RuntimeError(
                f"[{self._component_id}] IMX500 camera not opened. Call open() first."
            )
        return self._camera.capture_array("main")

    def info(self) -> dict:
        """Return IMX500 camera metadata."""
        status = "open" if self._camera is not None else "closed"
        result: dict[str, Any] = {
            "component_id": self._component_id,
            "device_type": self.device_type,
            "driver": self.driver,
            "status": status,
            "resolution": self._params.get("resolution"),
            "fps": self._params.get("fps"),
        }
        if self._imx500 is not None:
            result["camera_num"] = self._imx500.camera_num
        try:
            import picamera2  # type: ignore[import]
            result["picamera2_version"] = getattr(picamera2, "__version__", "unknown")
        except ImportError:
            pass
        return result
