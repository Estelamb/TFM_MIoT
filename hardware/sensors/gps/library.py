"""
AURA Generic Sensor Library: GPS
================================
"""
from hardware.utils import get_active_driver, load_specific_driver

class GPSSensor:
    LABEL = "GPS"

    def __init__(self, **kwargs):
        driver, params = get_active_driver("gps")
        if driver == "gps":
            driver = "gps_simulated"
        merged_params = {**params, **kwargs}
        driver_cls = load_specific_driver("sensors", "gps", driver)
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
        raise AttributeError("GPS driver has no read_value method")
