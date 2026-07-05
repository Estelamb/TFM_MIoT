"""
AURA MLOps Service Sensors Subpackage.
======================================
Exposes supported sensors catalog names and labels.
"""
from __future__ import annotations

def get_sensors() -> list[str]:
    """Returns a list of supported sensor identifiers.

    :return: List of sensors.
    :rtype: list
    """
    return [
        "camera/imx500",
        "camera/rpi_camera_module_3",
        "gps/gps_simulated",
        "template/dummy_sensor"
    ]

def get_sensors_data() -> dict[str, str]:
    """Returns a dictionary mapping sensor identifiers to human-readable labels.

    :return: Sensors mapping.
    :rtype: dict
    """
    return {
        "camera/imx500": "Sony IMX500 AI Camera",
        "camera/rpi_camera_module_3": "Raspberry Pi Camera Module 3",
        "gps/gps_simulated": "Simulated GPS Driver",
        "template/dummy_sensor": "Dummy Sensor"
    }
