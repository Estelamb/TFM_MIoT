import logging
from typing import Any
import numpy as np
from aura_hw.backends.base import InferenceBackend

logger = logging.getLogger(__name__)


class HailoBackend(InferenceBackend):
    """Hailo-8 / Hailo-8L PCIe AI accelerator backend.

    Uses the ``hailo_platform`` SDK (included in HailoRT).
    """

    def __init__(self, hw_type: str = "hailo8") -> None:
        self._hw_type = hw_type
        self._target = None
        self._hef = None
        self._ng = None
        self._inp = None
        self._out = None

    def load(self, model_path: str) -> None:
        from hailo_platform import (  # type: ignore[import]
            HEF,
            FormatType,
            HailoSchedulingAlgorithm,
            InputVStreamParams,
            OutputVStreamParams,
            VDevice,
        )
        params = VDevice.create_params()
        params.scheduling_algorithm = HailoSchedulingAlgorithm.ROUND_ROBIN
        self._target = VDevice(params=params)
        self._hef = HEF(model_path)
        self._ng = self._target.configure(self._hef)[0]
        self._inp = InputVStreamParams.make(self._ng, format_type=FormatType.FLOAT32)
        self._out = OutputVStreamParams.make(self._ng, format_type=FormatType.FLOAT32)
        logger.info(f"Hailo model loaded: {model_path}")

    def infer(self, inputs: "np.ndarray | dict | None") -> Any:
        from hailo_platform import InferVStreams  # type: ignore[import]
        with InferVStreams(self._ng, self._inp, self._out) as pipeline:
            with self._ng.activate():
                if isinstance(inputs, np.ndarray):
                    data = {list(self._inp.keys())[0]: inputs}
                else:
                    data = inputs
                pipeline.send(data)
                return pipeline.recv()

    def unload(self) -> None:
        if self._target:
            self._target.release()
            self._target = None
        logger.info("Hailo model unloaded")

    @property
    def hardware_type(self) -> str:
        return self._hw_type

    def device_info(self) -> dict:
        """Return Hailo accelerator metadata.

        Queries the HailoRT SDK for device identity when a session is active.
        Falls back to static info if the SDK is not available.
        """
        info: dict = {
            "hardware_type": self._hw_type,
            "accelerator": self._hw_type.upper(),
            "sdk": "hailo_platform",
        }
        try:
            from hailo_platform import HailoRTVersion  # type: ignore[import]
            info["sdk_version"] = HailoRTVersion()
        except Exception:  # noqa: BLE001
            pass
        return info
