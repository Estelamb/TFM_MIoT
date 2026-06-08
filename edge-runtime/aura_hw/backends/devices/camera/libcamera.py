"""
Libcamera Camera Backend
=========================
Raspberry Pi native camera backend using ``libcamera`` + ``picamera2``
*without* the IMX500 AI Camera extension.  Suitable for:

* Official RPi Camera Module v2 / v3 (OmniVision OV5647, Sony IMX219/708)
* Third-party CSI cameras supported by libcamera on RPi OS

Requires: ``picamera2`` (included in RPi OS; ``pip install picamera2`` elsewhere)

Configuration example in ``components_config.yaml``
----------------------------------------------------
::

    - id: camera_0
      type: camera
      driver: libcamera
      enabled: true
      params:
        resolution: [640, 480]
        fps: 10
        camera_index: 0     # index when multiple CSI cameras are present
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

from aura_hw.backends.devices.camera.base import CameraBackend

logger = logging.getLogger(__name__)


class LibcameraBackend(CameraBackend):
    """Raspberry Pi libcamera camera backend via picamera2.

    Uses ``picamera2`` in still/video capture mode without the IMX500
    neural-network pipeline — pure frame capture only.

    Parameters
    ----------
    component_id:
        Unique component identifier from ``components_config.yaml``.
    """

    def __init__(self, component_id: str) -> None:
        super().__init__(component_id)
        self._camera = None
        self._params: dict = {}

    # ── DeviceBackend interface ──────────────────────────────────────────────

    @property
    def driver(self) -> str:
        return "libcamera"

    def open(self, params: dict) -> None:
        """Initialise the libcamera camera.

        Args:
            params: Configuration dict with keys:

                * ``resolution`` (list[int]): ``[width, height]``.
                * ``fps`` (int): Target frame rate.
                * ``camera_index`` (int): Camera index when multiple
                  CSI cameras are attached (default 0).
        """
        from picamera2 import Picamera2  # type: ignore[import]

        self._params = params
        camera_index = params.get("camera_index", 0)
        resolution = params.get("resolution", [640, 480])
        fps = params.get("fps", 10)

        self._camera = Picamera2(camera_index)
        config = self._camera.create_video_configuration(
            main={"size": tuple(resolution), "format": "BGR888"},
            controls={"FrameRate": fps},
        )
        self._camera.configure(config)
        self._camera.start()
        logger.info(
            f"[{self._component_id}] libcamera opened: "
            f"index={camera_index} res={resolution} fps={fps}"
        )

    def close(self) -> None:
        """Stop and release the camera."""
        if self._camera is not None:
            self._camera.stop()
            self._camera = None
            logger.info(f"[{self._component_id}] libcamera closed")

    def capture_frame(self) -> np.ndarray:
        """Capture the latest frame from the CSI camera.

        Returns:
            BGR ``numpy.ndarray`` of shape ``(H, W, 3)``.

        Raises:
            RuntimeError: If the camera has not been opened.
        """
        if self._camera is None:
            raise RuntimeError(
                f"[{self._component_id}] libcamera not opened. Call open() first."
            )
        # capture_array returns a numpy array in the configured format
        frame = self._camera.capture_array("main")
        return frame

    def info(self) -> dict:
        """Return libcamera device metadata."""
        status = "open" if self._camera is not None else "closed"
        result: dict[str, Any] = {
            "component_id": self._component_id,
            "device_type": self.device_type,
            "driver": self.driver,
            "status": status,
            "camera_index": self._params.get("camera_index", 0),
            "resolution": self._params.get("resolution"),
            "fps": self._params.get("fps"),
        }
        try:
            import picamera2  # type: ignore[import]
            result["picamera2_version"] = getattr(picamera2, "__version__", "unknown")
        except ImportError:
            pass
        if self._camera is not None:
            try:
                camera_props = self._camera.camera_properties
                result["sensor_model"] = camera_props.get("Model", "unknown")
            except Exception:  # noqa: BLE001
                pass
        return result
