"""
AURA MLOps Service Actuators Subpackage.
=========================================
Exposes the supported actuators catalog names and information labels mapping.
"""
from __future__ import annotations

def get_actuators() -> list[str]:
    """Returns a list of supported actuator identifiers.

    :return: List of actuators.
    :rtype: list
    """
    return ["template/dummy_actuator"]

def get_actuators_data() -> dict[str, str]:
    """Returns a dictionary mapping actuator identifiers to human-readable labels.

    :return: Actuators mapping.
    :rtype: dict
    """
    return {
        "template/dummy_actuator": "Dummy Actuator"
    }
