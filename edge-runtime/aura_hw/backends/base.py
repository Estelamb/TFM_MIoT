"""
Abstract base class for all AURA inference backends.

Each hardware target (Hailo, TFLite, IMX500, TensorRT) implements this
interface so the rest of the runtime is fully hardware-agnostic.
"""
from abc import ABC, abstractmethod
from typing import Any

import numpy as np


class InferenceBackend(ABC):
    """Hardware-specific inference backend interface.

    Concrete subclasses must implement :meth:`load`, :meth:`infer` and
    :meth:`unload`.  The :attr:`hardware_type` property must return the
    canonical hardware identifier string used throughout the platform.
    """

    @abstractmethod
    def load(self, model_path: str) -> None:
        """Load a compiled model file into the accelerator.

        Args:
            model_path: Absolute path to the compiled model.
                        The expected format depends on the backend
                        (e.g. ``.hef`` for Hailo, ``.tflite`` for RPi CPU).

        Raises:
            RuntimeError: If the required SDK is not installed.
            FileNotFoundError: If ``model_path`` does not exist.
        """
        ...

    @abstractmethod
    def infer(self, inputs: "np.ndarray | dict | None") -> Any:
        """Execute a single inference pass.

        Args:
            inputs: Input tensor(s). Pass ``None`` for sensor-driven backends
                    (e.g. IMX500) where the hardware captures input internally.

        Returns:
            Raw model outputs. Structure varies by backend.
        """
        ...

    @abstractmethod
    def unload(self) -> None:
        """Release the model and free all accelerator resources."""
        ...

    @property
    @abstractmethod
    def hardware_type(self) -> str:
        """Canonical hardware identifier for this backend.

        Returns:
            One of ``"hailo8"``, ``"hailo8l"``, ``"rpi_ai_cam"``,
            ``"rpi"``, ``"jetson_orin_nano"``.
        """
        ...
