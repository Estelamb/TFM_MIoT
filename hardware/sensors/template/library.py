"""
AURA Generic Sensor Library: Template Category
==============================================
"""
from hardware.utils import get_active_driver, load_specific_driver

class TemplateSensor:
    def __init__(self, **kwargs):
        driver, params = get_active_driver("template")
        # Fallback to dummy_sensor if default driver is specified
        if driver == "template":
            driver = "dummy_sensor"
        merged_params = {**params, **kwargs}
        driver_cls = load_specific_driver("sensors", "template", driver)
        try:
            self._delegate = driver_cls(**merged_params)
        except TypeError:
            self._delegate = driver_cls()

    def initialize(self) -> bool:
        if hasattr(self._delegate, "initialize"):
            return self._delegate.initialize()
        return True

    def read_value(self):
        if hasattr(self._delegate, "read_value"):
            return self._delegate.read_value()
        raise AttributeError("Template driver has no read_value method")

# Module-level convenience functions using a default global instance
_default_sensor = None

def _get_default_sensor():
    global _default_sensor
    if _default_sensor is None:
        _default_sensor = TemplateSensor()
        _default_sensor.initialize()
    return _default_sensor

def initialize() -> bool:
    return _get_default_sensor().initialize()

def read_value():
    return _get_default_sensor().read_value()
