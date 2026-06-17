"""
AURA Generic Sensor Library: Camera
===================================
"""
from hardware.utils import get_active_driver, load_specific_driver

class Camera:
    def __init__(self, **kwargs):
        driver, params = get_active_driver("camera")
        # Map built-in drivers to rpi_camera_module_3 for local simulation/scripts
        if driver in ("opencv", "libcamera", "imx500", "template"):
            driver = "rpi_camera_module_3"
        merged_params = {**params, **kwargs}
        driver_cls = load_specific_driver("sensors", "camera", driver)
        try:
            self._delegate = driver_cls(**merged_params)
        except TypeError:
            self._delegate = driver_cls()

    def initialize(self) -> bool:
        if hasattr(self._delegate, "initialize"):
            return self._delegate.initialize()
        elif hasattr(self._delegate, "open"):
            self._delegate.open({})
            return True
        return True

    def take_photo(self):
        if hasattr(self._delegate, "read_value"):
            return self._delegate.read_value()
        elif hasattr(self._delegate, "capture_frame"):
            return self._delegate.capture_frame()
        elif hasattr(self._delegate, "read"):
            return self._delegate.read()
        raise AttributeError("Camera driver has no capture/read method")

    def read_value(self):
        return self.take_photo()

    def close(self) -> None:
        if hasattr(self._delegate, "close"):
            self._delegate.close()

# Module-level convenience functions using a default global instance
_default_camera = None

def _get_default_camera():
    global _default_camera
    if _default_camera is None:
        _default_camera = Camera()
        _default_camera.initialize()
    return _default_camera

def initialize() -> bool:
    return _get_default_camera().initialize()

def take_photo():
    return _get_default_camera().take_photo()

def read_value():
    return _get_default_camera().read_value()

def close() -> None:
    global _default_camera
    if _default_camera is not None:
        _default_camera.close()
        _default_camera = None
