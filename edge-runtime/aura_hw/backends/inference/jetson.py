import logging
from typing import Any

from aura_hw.backends.inference.base import InferenceBackend

logger = logging.getLogger(__name__)


class JetsonTRTBackend(InferenceBackend):
    """NVIDIA Jetson Orin Nano — TensorRT inference backend.

    .. note::
        This backend is a **stub**.  Full TensorRT integration is pending.
        ``load()`` records the model path and ``infer()`` returns an empty
        dict while logging a warning on every call.
    """

    def __init__(self) -> None:
        self._engine = None
        self._model_path: str | None = None

    def load(self, model_path: str) -> None:
        self._model_path = model_path
        logger.warning(
            "JetsonTRTBackend: stub — TensorRT engine loading not yet implemented. "
            f"Model path recorded: {model_path}"
        )

    def infer(self, inputs: Any) -> dict:
        logger.warning("JetsonTRTBackend: infer() is a stub — returning empty output")
        return {}

    def unload(self) -> None:
        self._engine = None
        self._model_path = None

    @property
    def hardware_type(self) -> str:
        return "jetson_orin_nano"

    def device_info(self) -> dict:
        """Return Jetson hardware metadata."""
        info: dict = {
            "hardware_type": "jetson_orin_nano",
            "accelerator": "NVIDIA Jetson Orin Nano (TensorRT stub)",
            "model_path": self._model_path,
        }
        try:
            with open("/etc/nv_tegra_release") as fh:
                info["tegra_release"] = fh.read().strip()
        except OSError:
            pass
        return info
