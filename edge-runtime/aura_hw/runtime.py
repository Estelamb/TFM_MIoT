"""
Public API for the AURA hardware abstraction layer.

Exposes five functions for inference scripts and the PAL layer:

* :func:`load_model`        — load a compiled model onto the detected hardware
* :func:`execute_inference` — run one inference pass
* :func:`unload_model`      — release the model and free accelerator resources
* :func:`get_hardware_info` — return a dict describing the current hardware state
* :func:`get_last_inference`— return the result of the last inference pass

The correct inference backend is selected automatically via
:func:`~aura_hw.detect.detect_hardware`.

Device backends (cameras, sensors) are managed separately by
:class:`~aura_hw.device_manager.DeviceManager`.
"""
import logging
from typing import Any

import numpy as np

from aura_hw.detect import detect_hardware
from aura_hw.backends.inference.base import InferenceBackend

logger = logging.getLogger(__name__)

_backend: InferenceBackend | None = None
_last_inference: Any = None


def _get_backend(hw: str) -> InferenceBackend:
    """Instantiate the inference backend for the given hardware type.

    All backends are loaded dynamically from the ``hardware/`` directory,
    which is populated via OTA when the device connects to the platform.

    Args:
        hw: Hardware identifier returned by :func:`~aura_hw.detect.detect_hardware`.

    Returns:
        A concrete :class:`~aura_hw.backends.inference.base.InferenceBackend`.

    Raises:
        RuntimeError: If ``hw`` is ``"unknown"`` or the required library
            has not been downloaded yet.
    """
    if hw == "unknown":
        raise RuntimeError(
            "Hardware type is 'unknown'. Set AURA_HARDWARE_TYPE or ensure "
            "auto-detection can identify your hardware."
        )

    from aura_hw.loader import get_hardware_dir
    hw_dir = get_hardware_dir()
    custom_lib = hw_dir / "hw_arch" / hw / "inference" / "library.py"

    if not custom_lib.exists():
        raise RuntimeError(
            f"No inference library found for hardware type '{hw}' at "
            f"{custom_lib}. The hardware libraries have not been downloaded "
            "yet. Connect to the AURA platform to receive them via OTA "
            "(update_libraries command)."
        )

    from aura_hw.backends.inference.general import GeneralInferenceBackend
    return GeneralInferenceBackend(hw)


def load_model(model_path: str) -> None:
    global _backend
    hw = detect_hardware()
    logger.info(f"Hardware detected: {hw}")
    backend = _get_backend(hw)
    backend.load(model_path)
    _backend = backend


def execute_inference(inputs: "np.ndarray | dict | None" = None) -> Any:
    """Run a single inference pass with the currently loaded model.

    Args:
        inputs: Input tensor(s) for the model.

                * For Hailo and ONNX: a ``numpy.ndarray`` (NCHW for YOLOv8)
                  or a ``dict`` mapping input names to arrays.
                * For RPi AI Camera (IMX500): pass ``None`` — the sensor
                  captures and runs inference internally.

    Returns:
        Raw model outputs. Structure depends on the backend:

        * Hailo: ``dict[str, numpy.ndarray]``
        * ONNX: ``dict[str, numpy.ndarray]``
        * IMX500: output from ``IMX500.get_outputs(metadata)``

    Raises:
        RuntimeError: If :func:`load_model` has not been called yet.

    Example:
        >>> import numpy as np
        >>> tensor = np.zeros((1, 3, 640, 640), dtype=np.float32)
        >>> outputs = execute_inference(tensor)
    """
    global _last_inference
    if _backend is None:
        raise RuntimeError(
            "No model loaded. Call load_model() before execute_inference()."
        )
    result = _backend.infer(inputs)
    _last_inference = result
    return result


def unload_model() -> None:
    """Unload the current model and release accelerator resources.

    Safe to call even if no model is loaded (no-op in that case).
    """
    global _backend, _last_inference
    if _backend:
        _backend.unload()
        _backend = None
    _last_inference = None


def get_hardware_info() -> dict:
    """Return a snapshot of the current hardware and model state.

    Returns:
        A dict with the following keys:

        * ``hardware_type`` (str): Detected hardware identifier.
        * ``model_loaded`` (bool): Whether a model is currently loaded.
        * ``backend`` (str | None): Class name of the active backend,
          or ``None`` if no model is loaded.
        * ``device_info`` (dict): Accelerator-specific metadata from
          :meth:`~aura_hw.backends.inference.base.InferenceBackend.device_info`.

    Example:
        >>> info = get_hardware_info()
        >>> print(info)
        {'hardware_type': 'hailo8', 'model_loaded': True,
         'backend': 'HailoBackend', 'device_info': {...}}
    """
    hw = detect_hardware()
    return {
        "hardware_type": hw,
        "model_loaded": _backend is not None,
        "backend": type(_backend).__name__ if _backend else None,
        "device_info": _backend.device_info() if _backend else {},
    }


def get_last_inference() -> Any:
    """Return the result of the most recent :func:`execute_inference` call.

    Allows the telemetry loop to read the latest inference result without
    triggering a new inference pass.

    Returns:
        The last inference output, or ``None`` if no inference has been
        run yet in this session.
    """
    return _last_inference


def get_model_classes() -> list[str]:
    """Return the list of class names loaded from the current model's metadata."""
    if _backend:
        return _backend.device_info().get("class_names", [])
    return []
