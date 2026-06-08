"""
OpenCV Camera Backend
======================
Generic camera backend using OpenCV ``VideoCapture``.  Works with:

* USB webcams (source = device index, e.g. ``0``)
* CSI cameras exposed as V4L2 devices
* RTSP / HTTP streams (source = URL string)
* Video files (source = file path string, useful for testing)

Requires: ``opencv-python-headless`` (or ``opencv-python``)

Configuration example in ``components_config.yaml``
----------------------------------------------------
::

    - id: camera_0
      type: camera
      driver: opencv
      enabled: true
      params:
        source: 0            # int device index, or "rtsp://..." / file path
        resolution: [640, 480]
        fps: 10
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

from aura_hw.backends.devices.camera.base import CameraBackend

logger = logging.getLogger(__name__)


class OpenCVCameraBackend(CameraBackend):
    """Generic OpenCV camera backend.

    Parameters
    ----------
    component_id:
        Unique component identifier from ``components_config.yaml``.
    """

    def __init__(self, component_id: str) -> None:
        super().__init__(component_id)
        self._cap = None
        self._params: dict = {}

    # ── DeviceBackend interface ──────────────────────────────────────────────

    @property
    def driver(self) -> str:
        return "opencv"

    def open(self, params: dict) -> None:
        """Open the video capture source.

        Args:
            params: Configuration dict with keys:

                * ``source`` (int | str): Device index, RTSP URI, or file path.
                * ``resolution`` (list[int]): ``[width, height]`` (optional).
                * ``fps`` (int): Target frame rate (optional, best-effort).
        """
        import cv2  # type: ignore[import]

        self._params = params
        source = params.get("source", 0)
        # Accept string indices as integers
        if isinstance(source, str) and source.isdigit():
            source = int(source)

        self._cap = cv2.VideoCapture(source)
        if not self._cap.isOpened():
            raise OSError(
                f"[{self._component_id}] OpenCV could not open camera source: {source!r}"
            )

        resolution = params.get("resolution")
        if resolution and len(resolution) == 2:
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])

        fps = params.get("fps")
        if fps:
            self._cap.set(cv2.CAP_PROP_FPS, fps)

        logger.info(
            f"[{self._component_id}] OpenCV camera opened: source={source!r} "
            f"res={resolution} fps={fps}"
        )

    def close(self) -> None:
        """Release the VideoCapture handle."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            logger.info(f"[{self._component_id}] OpenCV camera closed")

    def capture_frame(self) -> np.ndarray:
        """Capture the next frame from the video source.

        Returns:
            BGR ``numpy.ndarray`` of shape ``(H, W, 3)``.

        Raises:
            RuntimeError: If the camera has not been opened or capture fails.
        """
        if self._cap is None:
            raise RuntimeError(
                f"[{self._component_id}] Camera not opened. Call open() first."
            )
        ret, frame = self._cap.read()
        if not ret or frame is None:
            raise IOError(
                f"[{self._component_id}] Failed to capture frame from OpenCV source."
            )
        return frame

    def info(self) -> dict:
        """Return camera state and capability metadata."""
        status = "open" if self._cap is not None and self._cap.isOpened() else "closed"
        result: dict[str, Any] = {
            "component_id": self._component_id,
            "device_type": self.device_type,
            "driver": self.driver,
            "status": status,
            "source": self._params.get("source"),
        }
        if self._cap is not None and self._cap.isOpened():
            import cv2  # type: ignore[import]
            result["actual_width"]  = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            result["actual_height"] = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            result["actual_fps"]    = round(self._cap.get(cv2.CAP_PROP_FPS), 1)
        try:
            import cv2  # type: ignore[import]
            result["opencv_version"] = cv2.__version__
        except ImportError:
            pass
        return result
