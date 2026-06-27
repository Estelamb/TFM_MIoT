"""
AURA Generic Actuator Library: Template Category
================================================
"""
from hardware.utils import get_active_driver, load_specific_driver

class TemplateActuator:
    LABEL = "Template"
    
    def __init__(self, **kwargs):
        driver, params = get_active_driver("template")
        if driver == "template":
            driver = "dummy_actuator"
        merged_params = {**params, **kwargs}
        driver_cls = load_specific_driver("actuators", "template", driver)
        try:
            self._delegate = driver_cls(**merged_params)
        except TypeError:
            self._delegate = driver_cls()

    def initialize(self) -> bool:
        if hasattr(self._delegate, "initialize"):
            return self._delegate.initialize()
        return True

    def write_value(self, value) -> None:
        if hasattr(self._delegate, "write_value"):
            self._delegate.write_value(value)
        else:
            raise AttributeError("Template driver has no write_value method")

# Module-level convenience functions using a default global instance
_default_actuator = None

def _get_default_actuator():
    global _default_actuator
    if _default_actuator is None:
        _default_actuator = TemplateActuator()
        _default_actuator.initialize()
    return _default_actuator

def initialize() -> bool:
    return _get_default_actuator().initialize()

def write_value(value) -> None:
    _get_default_actuator().write_value(value)
