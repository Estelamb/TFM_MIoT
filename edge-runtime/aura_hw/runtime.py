"""
Public API for the AURA hardware abstraction layer.

Exposes four functions that inference scripts should use:

* :func:`load_model` — load a compiled model onto the detected hardware
* :func:`execute_inference` — run one inference pass
* :func:`unload_model` — release the model and free accelerator resources
* :func:`get_hardware_info` — return a dict describing the current state

The correct backend is selected automatically based on
:func:`~aura_hw.detect.detect_hardware`.
"""
import logging
from typing import Any

import numpy as np

from aura_hw.detect import detect_hardware
from aura_hw.backends.base import InferenceBackend

logger = logging.getLogger(__name__)

_backend: InferenceBackend | None = None


def _get_backend(hw: str) -> InferenceBackend:
    """Instantiate the backend for the given hardware type.

    Args:
        hw: Hardware identifier returned by :func:`~aura_hw.detect.detect_hardware`.

    Returns:
        A concrete :class:`~aura_hw.backends.base.InferenceBackend` instance.
    """
    if hw in ("hailo8", "hailo8l"):
        from aura_hw.backends.hailo import HailoBackend
        return HailoBackend(hw)
    if hw == "rpi_ai_cam":
        from aura_hw.backends.rpi_ai_cam import RPiAICamBackend
        return RPiAICamBackend()
    if hw == "jetson_orin_nano":
        from aura_hw.backends.jetson import JetsonTRTBackend
        return JetsonTRTBackend()
    from aura_hw.backends.rpi_tflite import RPiTFLiteBackend
    return RPiTFLiteBackend()


def load_model(model_path: str) -> None:
    """Detect hardware and load a compiled model.

    Calls :func:`~aura_hw.detect.detect_hardware`, selects the matching
    backend, and invokes its :meth:`~aura_hw.backends.base.InferenceBackend.load`
    method.  Any previously loaded model is **not** automatically unloaded —
    call :func:`unload_model` first if you need to swap models.

    Args:
        model_path: Absolute path to the compiled model file
                    (``.hef`` for Hailo, ``packerOut.zip`` for IMX500,
                    ``.tflite`` for CPU).

    Example:
        >>> from aura_hw import load_model, execute_inference
        >>> load_model("/tmp/aura/model")
    """
    global _backend
    hw = detect_hardware()
    logger.info(f"Hardware detected: {hw}")
    _backend = _get_backend(hw)
    _backend.load(model_path)


def execute_inference(inputs: "np.ndarray | dict | None" = None) -> Any:
    """Run a single inference pass with the currently loaded model.

    Args:
        inputs: Input tensor(s) for the model.

                * For Hailo and TFLite: a ``numpy.ndarray`` (NCHW for YOLOv8)
                  or a ``dict`` mapping input names to arrays.
                * For RPi AI Camera (IMX500): pass ``None`` — the sensor
                  captures and runs inference internally.

    Returns:
        Raw model outputs. The exact structure depends on the backend:

        * Hailo: ``dict[str, numpy.ndarray]``
        * TFLite: ``dict[str, numpy.ndarray]``
        * IMX500: output from ``IMX500.get_outputs(metadata)``

    Raises:
        RuntimeError: If :func:`load_model` has not been called yet.

    Example:
        >>> import numpy as np
        >>> tensor = np.zeros((1, 3, 640, 640), dtype=np.float32)
        >>> outputs = execute_inference(tensor)
    """
    if _backend is None:
        raise RuntimeError(
            "No model loaded. Call load_model() before execute_inference()."
        )
    return _backend.infer(inputs)


def unload_model() -> None:
    """Unload the current model and release accelerator resources.

    Safe to call even if no model is loaded (no-op in that case).
    """
    global _backend
    if _backend:
        _backend.unload()
        _backend = None


def get_hardware_info() -> dict:
    """Return a snapshot of the current hardware and model state.

    Returns:
        A dict with the following keys:

        * ``hardware_type`` (str): Detected hardware identifier.
        * ``model_loaded`` (bool): Whether a model is currently loaded.
        * ``backend`` (str | None): Class name of the active backend,
          or ``None`` if no model is loaded.

    Example:
        >>> info = get_hardware_info()
        >>> print(info)
        {'hardware_type': 'hailo8', 'model_loaded': True, 'backend': 'HailoBackend'}
    """
    hw = detect_hardware()
    return {
        "hardware_type": hw,
        "model_loaded": _backend is not None,
        "backend": type(_backend).__name__ if _backend else None,
    }
