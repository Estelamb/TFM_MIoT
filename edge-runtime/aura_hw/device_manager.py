"""
AURA Device Manager
=====================
Reads ``components_config.yaml``, instantiates the correct device
backend for each enabled component, and manages their lifecycle.

All device backends are loaded dynamically from the ``hardware/``
directory, which is populated via OTA when the device connects to
the AURA platform.

Usage
-----
::

    from pathlib import Path
    from aura_hw.device_manager import DeviceManager

    dm = DeviceManager(Path("config/components_config.yaml"))
    dm.open_all()

    frame = dm.get_device("camera_0").capture_frame()
    reading = dm.get_device("env_sensor_0").measure()

    dm.close_all()
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from aura_hw.backends.devices.base import DeviceBackend

logger = logging.getLogger(__name__)


# ── Dynamic factories ────────────────────────────────────────────────────────
# All backends are loaded dynamically from hardware/<category>/<driver>/library.py.

def _make_camera(cid: str, driver: str) -> DeviceBackend:
    from aura_hw.backends.devices.camera.general import GeneralCameraBackend
    return GeneralCameraBackend(cid, driver)

def _make_sensor(cid: str, driver: str) -> DeviceBackend:
    from aura_hw.backends.devices.sensor.general import GeneralSensorBackend
    return GeneralSensorBackend(cid, driver)

def _make_temperature(cid: str, driver: str) -> DeviceBackend:
    from aura_hw.backends.devices.sensor.temperature import GeneralTemperatureSensor
    return GeneralTemperatureSensor(cid, driver)

def _make_distance(cid: str, driver: str) -> DeviceBackend:
    from aura_hw.backends.devices.sensor.distance import GeneralDistanceSensor
    return GeneralDistanceSensor(cid, driver)

def _make_imu(cid: str, driver: str) -> DeviceBackend:
    from aura_hw.backends.devices.sensor.imu import GeneralIMUSensor
    return GeneralIMUSensor(cid, driver)

def _make_led(cid: str, driver: str) -> DeviceBackend:
    from aura_hw.backends.devices.actuator.led import GeneralLEDActuator
    return GeneralLEDActuator(cid, driver)

def _make_buzzer(cid: str, driver: str) -> DeviceBackend:
    from aura_hw.backends.devices.actuator.buzzer import GeneralBuzzerActuator
    return GeneralBuzzerActuator(cid, driver)

def _make_servo(cid: str, driver: str) -> DeviceBackend:
    from aura_hw.backends.devices.actuator.servo import GeneralServoActuator
    return GeneralServoActuator(cid, driver)

def _make_relay(cid: str, driver: str) -> DeviceBackend:
    from aura_hw.backends.devices.actuator.relay import GeneralRelayActuator
    return GeneralRelayActuator(cid, driver)


# Maps device type → dynamic factory
_TYPE_FACTORIES: dict[str, callable] = {
    "camera": _make_camera,
    "sensor": _make_sensor,
    "temperature": _make_temperature,
    "distance": _make_distance,
    "imu": _make_imu,
    "led": _make_led,
    "buzzer": _make_buzzer,
    "servo": _make_servo,
    "relay": _make_relay,
}


class DeviceManager:
    """Lifecycle manager for all connected device backends.

    Reads ``components_config.yaml``, instantiates one backend per
    enabled component, and exposes a keyed-access API.

    Parameters
    ----------
    config_path:
        Absolute path to ``components_config.yaml``.
    """

    def __init__(self, config_path: Path) -> None:
        self._config_path = config_path
        self._devices: dict[str, DeviceBackend] = {}
        self._component_params: dict[str, dict] = {}
        self._load_config()

    # ── Public API ────────────────────────────────────────────────────────────

    def open_all(self) -> None:
        """Open all enabled device backends.

        Skips components whose drivers are not registered or that fail
        to open (logs an error but does not raise).
        """
        for component_id, backend in self._devices.items():
            params = self._component_params.get(component_id, {})
            try:
                backend.open(params)
                logger.info(
                    f"[DeviceManager] Opened: {component_id} "
                    f"({backend.device_type}/{backend.driver})"
                )
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    f"[DeviceManager] Failed to open {component_id}: {exc}"
                )

    def close_all(self) -> None:
        """Close all open device backends in reverse instantiation order."""
        for component_id, backend in reversed(list(self._devices.items())):
            try:
                backend.close()
                logger.info(f"[DeviceManager] Closed: {component_id}")
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    f"[DeviceManager] Error closing {component_id}: {exc}"
                )

    def get_device(self, component_id: str) -> DeviceBackend:
        """Return the backend for a specific component.

        Args:
            component_id: The ``id`` field from ``components_config.yaml``.

        Returns:
            The instantiated :class:`~aura_hw.backends.devices.base.DeviceBackend`.

        Raises:
            KeyError: If no enabled component with that ID exists.
        """
        if component_id not in self._devices:
            available = list(self._devices.keys())
            raise KeyError(
                f"No enabled device with id '{component_id}'. "
                f"Available: {available}"
            )
        return self._devices[component_id]

    def get_all_info(self) -> dict[str, dict]:
        """Return ``info()`` for every managed device.

        Returns:
            Dict mapping ``component_id → info_dict``.
        """
        result: dict[str, dict] = {}
        for component_id, backend in self._devices.items():
            try:
                result[component_id] = backend.info()
            except Exception as exc:  # noqa: BLE001
                result[component_id] = {"error": str(exc)}
        return result

    def list_components(self) -> list[str]:
        """Return the IDs of all managed (enabled) components."""
        return list(self._devices.keys())

    # ── Internal ──────────────────────────────────────────────────────────────

    def _load_config(self) -> None:
        """Parse the YAML config and instantiate backends for enabled components."""
        try:
            with open(self._config_path) as fh:
                raw = yaml.safe_load(fh) or {}
        except FileNotFoundError:
            logger.warning(
                f"[DeviceManager] components_config.yaml not found at "
                f"{self._config_path} — no devices will be managed."
            )
            return
        except Exception as exc:  # noqa: BLE001
            logger.error(f"[DeviceManager] Failed to read config: {exc}")
            return

        components = raw.get("components", [])
        for entry in components:
            if not entry.get("enabled", True):
                logger.debug(
                    f"[DeviceManager] Skipping disabled component: {entry.get('id')}"
                )
                continue

            component_id = entry.get("id", "<unnamed>")
            device_type  = entry.get("type", "")
            driver       = entry.get("driver", "")
            params       = entry.get("params", {})

            type_factory = _TYPE_FACTORIES.get(device_type)
            if type_factory is None:
                logger.warning(
                    f"[DeviceManager] No backend factory for "
                    f"type='{device_type}' driver='{driver}' "
                    f"(component: {component_id}). Skipping."
                )
                continue

            try:
                backend = type_factory(component_id, driver)
                self._devices[component_id] = backend
                self._component_params[component_id] = params
                logger.debug(
                    f"[DeviceManager] Registered: {component_id} → "
                    f"{type(backend).__name__}"
                )
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    f"[DeviceManager] Failed to instantiate backend for "
                    f"{component_id}: {exc}"
                )

