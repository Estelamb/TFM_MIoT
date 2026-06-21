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

    # Probe Host Hardware Daemon for hardware_type
    try:
        import socket
        import urllib.request
        import json
        
        gw_ip = "172.18.0.1"
        try:
            with open("/proc/net/route") as f:
                for line in f:
                    fields = line.strip().split()
                    if len(fields) >= 3 and fields[1] == '00000000':
                        hex_gw = fields[2]
                        gw_ip = socket.inet_ntoa(bytes.fromhex(hex_gw)[::-1])
                        break
        except Exception:
            pass
            
        mqtt_host = os.environ.get("AURA_MQTT_HOST")
        if mqtt_host and mqtt_host not in ("mosquitto", "aura-mosquitto", "localhost", "127.0.0.1"):
            gw_ip = mqtt_host
            
        daemon_url = f"http://{gw_ip}:8008"
        with urllib.request.urlopen(f"{daemon_url}/status", timeout=2.0) as resp:
            if resp.status == 200:
                status_data = json.loads(resp.read().decode("utf-8"))
                detected_hw = status_data.get("hardware_type")
                if detected_hw:
                    return detected_hw
    except Exception:
        pass

    # Hailo PCIe accelerator (local fallback if running on host/standalone)
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
