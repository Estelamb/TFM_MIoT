"""
Hardware auto-detection for the AURA edge runtime.

Probes the host system to determine which AI accelerator is available.
The result is cached after the first call so repeated imports don't
re-run the detection logic.

Detection order
---------------
1. ``AURA_HARDWARE_TYPE`` environment variable (override, highest priority)
2. ``hailortcli fw-control identify`` → ``hailo8`` / ``hailo8l``
3. ``/etc/nv_tegra_release`` → ``jetson_orin_nano``
4. ``libcamera-hello --list-cameras`` with *imx500* in output → ``rpi_ai_cam``
5. ``/proc/device-tree/model`` containing *raspberry* → ``rpi``
6. Fallback → ``unknown``

If the result is ``"unknown"``, :func:`~aura_hw.runtime.load_model` will
raise :exc:`RuntimeError`.  Set ``AURA_HARDWARE_TYPE`` to a supported
target to override auto-detection.
"""
import os
import subprocess
from functools import lru_cache


@lru_cache(maxsize=1)
def detect_hardware() -> str:
    """Detect the available AI hardware on the current device.

    The result is cached after the first successful call via
    :func:`functools.lru_cache`.

    Returns:
        A hardware identifier string. One of:

        * ``"hailo8"``
        * ``"hailo8l"``
        * ``"jetson_orin_nano"``
        * ``"rpi_ai_cam"``
        * ``"rpi"``
        * ``"unknown"``

    Note:
        Set the environment variable ``AURA_HARDWARE_TYPE`` to bypass
        auto-detection entirely::

            AURA_HARDWARE_TYPE=hailo8 python agent.py
    """
    override = os.environ.get("AURA_HARDWARE_TYPE")
    if override:
        return override.lower()

    # Hailo PCIe accelerator
    try:
        result = subprocess.run(
            ["hailortcli", "fw-control", "identify"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return "hailo8l" if "hailo8l" in result.stdout.lower() else "hailo8"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # NVIDIA Jetson
    if os.path.exists("/etc/nv_tegra_release"):
        return "jetson_orin_nano"

    # Raspberry Pi AI Camera (Sony IMX500)
    try:
        result = subprocess.run(
            ["libcamera-hello", "--list-cameras"],
            capture_output=True, text=True, timeout=5,
        )
        if "imx500" in result.stdout.lower():
            return "rpi_ai_cam"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Generic Raspberry Pi
    if os.path.exists("/proc/device-tree/model"):
        with open("/proc/device-tree/model") as f:
            if "raspberry" in f.read().lower():
                return "rpi"

    return "unknown"
