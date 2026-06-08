import logging
from typing import Any

import numpy as np

from aura_hw.backends.inference.base import InferenceBackend

logger = logging.getLogger(__name__)


class RPiTFLiteBackend(InferenceBackend):
    """Raspberry Pi CPU inference backend using TensorFlow Lite.

    Tries to import ``tflite_runtime`` first; falls back to the full
    ``tensorflow`` package if the lightweight runtime is not installed.
    Suitable for RPi 4/5 without a dedicated AI accelerator.
    """

    def __init__(self) -> None:
        self._interp = None
        self._inp = None
        self._out = None

    def load(self, model_path: str) -> None:
        try:
            from tflite_runtime.interpreter import Interpreter  # type: ignore[import]
        except ImportError:
            import tensorflow as tf  # type: ignore[import]
            Interpreter = tf.lite.Interpreter
        self._interp = Interpreter(model_path=model_path)
        self._interp.allocate_tensors()
        self._inp = self._interp.get_input_details()
        self._out = self._interp.get_output_details()
        logger.info(f"TFLite model loaded: {model_path}")

    def infer(self, inputs: "np.ndarray | dict | None") -> Any:
        if isinstance(inputs, np.ndarray):
            self._interp.set_tensor(self._inp[0]["index"], inputs)
        else:
            for detail in self._inp:
                self._interp.set_tensor(detail["index"], inputs[detail["name"]])
        self._interp.invoke()
        return {d["name"]: self._interp.get_tensor(d["index"]) for d in self._out}

    def unload(self) -> None:
        self._interp = None
        logger.info("TFLite model unloaded")

    @property
    def hardware_type(self) -> str:
        return "rpi"

    def device_info(self) -> dict:
        """Return TFLite backend metadata."""
        info: dict = {
            "hardware_type": "rpi",
            "accelerator": "CPU (TFLite)",
        }
        try:
            import tflite_runtime  # type: ignore[import]
            info["sdk"] = "tflite_runtime"
            info["sdk_version"] = getattr(tflite_runtime, "__version__", "unknown")
        except ImportError:
            try:
                import tensorflow as tf  # type: ignore[import]
                info["sdk"] = "tensorflow"
                info["sdk_version"] = tf.__version__
            except ImportError:
                info["sdk"] = "unknown"
        if self._inp:
            info["input_shape"] = self._inp[0].get("shape", []).tolist()
        return info
