import logging
from typing import Any
from aura_hw.backends.base import InferenceBackend

logger = logging.getLogger(__name__)


class RPiAICamBackend(InferenceBackend):
    """Raspberry Pi AI Camera (Sony IMX500) backend.

    Inference runs on the IMX500 image signal processor (ISP).
    The sensor captures frames and runs the model internally; calling
    ``infer()`` with ``inputs=None`` retrieves the latest outputs from
    the sensor metadata stream.
    """

    def __init__(self) -> None:
        self._camera = None
        self._imx500 = None

    def load(self, model_path: str) -> None:
        from picamera2 import Picamera2  # type: ignore[import]
        from picamera2.devices.imx500 import IMX500  # type: ignore[import]
        self._imx500 = IMX500(model_path)
        self._camera = Picamera2(self._imx500.camera_num)
        self._camera.configure(
            self._camera.create_preview_configuration(
                controls={"FrameRate": 10}
            )
        )
        self._camera.start()
        logger.info(f"RPi AI Camera model loaded: {model_path}")

    def infer(self, inputs: Any = None) -> Any:
        """Capture sensor metadata and return IMX500 model outputs.

        Args:
            inputs: Ignored — the IMX500 sensor drives inference internally.

        Returns:
            Raw IMX500 output tensors from the sensor metadata stream.
        """
        return self._imx500.get_outputs(self._camera.capture_metadata())

    def unload(self) -> None:
        if self._camera:
            self._camera.stop()
            self._camera = None
        self._imx500 = None
        logger.info("RPi AI Camera unloaded")

    @property
    def hardware_type(self) -> str:
        return "rpi_ai_cam"

    def device_info(self) -> dict:
        """Return IMX500 camera device metadata."""
        info: dict = {
            "hardware_type": "rpi_ai_cam",
            "accelerator": "IMX500 (on-sensor ISP)",
            "sdk": "picamera2",
        }
        try:
            import picamera2  # type: ignore[import]
            info["sdk_version"] = getattr(picamera2, "__version__", "unknown")
        except ImportError:
            pass
        if self._imx500 is not None:
            info["camera_num"] = self._imx500.camera_num
        return info
