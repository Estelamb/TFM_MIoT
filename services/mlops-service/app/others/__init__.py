"""
AURA MLOps Service Others Subpackage.
=====================================
Exposes other supported auxiliary peripheral catalog names and labels.
"""
from __future__ import annotations

def get_others() -> list[str]:
    """Returns a list of other supported peripheral identifiers.

    :return: List of peripherals.
    :rtype: list
    """
    return ["template/dummy_other"]

def get_others_data() -> dict[str, str]:
    """Returns a dictionary mapping peripheral identifiers to human-readable labels.

    :return: Peripherals mapping.
    :rtype: dict
    """
    return {
        "template/dummy_other": "Dummy Other Device"
    }
