import logging
from typing import Any

from aura_hw.backends.devices.actuator.base import ActuatorBackend
from aura_hw.loader import load_component_class

logger = logging.getLogger(__name__)

class GeneralServoActuator(ActuatorBackend):
    """
    General Servo Actuator library/wrapper.
    Dynamically loads custom servo actuator from hardware/actuators/servo/<driver>/library.py.
    """

    def __init__(self, component_id: str, driver: str) -> None:
        super().__init__(component_id)
        self._driver = driver
        self._delegate = None
        self._is_open = False

    @property
    def device_type(self) -> str:
        return "servo"

    @property
    def driver(self) -> str:
        return self._driver

    def open(self, params: dict) -> None:
        logger.info(f"[GeneralServoActuator] Dynamically loading custom servo driver '{self._driver}'")
        cls = load_component_class("actuators", "servo", self._driver)

        try:
            self._delegate = cls(**params)
        except TypeError:
            self._delegate = cls()

        if hasattr(self._delegate, "initialize"):
            success = self._delegate.initialize()
            if not success:
                raise OSError(f"Failed to initialize custom servo driver '{self._driver}'")
        elif hasattr(self._delegate, "open"):
            self._delegate.open(params)

        self._is_open = True

    def close(self) -> None:
        if self._delegate:
            if hasattr(self._delegate, "close"):
                self._delegate.close()
            self._delegate = None
        self._is_open = False

    def write(self, value: Any) -> None:
        if not self._is_open or self._delegate is None:
            raise RuntimeError(f"Servo actuator '{self.component_id}' is not open.")

        if hasattr(self._delegate, "write_value"):
            self._delegate.write_value(value)
        elif hasattr(self._delegate, "write"):
            self._delegate.write(value)
        else:
            raise AttributeError(f"Custom servo driver class has no write/write_value method")

    def info(self) -> dict:
        if self._delegate and hasattr(self._delegate, "info"):
            return self._delegate.info()

        return {
            "component_id": self.component_id,
            "device_type": self.device_type,
            "driver": self.driver,
            "status": "open" if self._is_open else "closed",
        }
