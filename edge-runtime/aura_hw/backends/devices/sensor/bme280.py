"""
BME280 Sensor Backend
======================
Environmental sensor (temperature, relative humidity, barometric
pressure) connected via I2C.

Sensor datasheet
    Bosch BME280 — https://www.bosch-sensortec.com/products/environmental-sensors/humidity-sensors-bme280/

Requires: ``smbus2`` and ``bme280`` (``pip install smbus2 RPi.bme280``)

Wiring (Raspberry Pi)
---------------------
BME280 VCC  → 3.3 V (pin 1)
BME280 GND  → GND   (pin 6)
BME280 SDA  → GPIO2 (pin 3, I2C1 SDA)
BME280 SCL  → GPIO3 (pin 5, I2C1 SCL)

Default I2C address: ``0x76`` (SDO → GND) or ``0x77`` (SDO → VCC).

Configuration example in ``components_config.yaml``
----------------------------------------------------
::

    - id: env_sensor_0
      type: sensor
      driver: bme280
      enabled: true
      params:
        protocol: i2c
        bus: 1           # I2C bus number (1 on RPi 3/4/5)
        address: "0x76"  # hex string or int
        measurements: [temperature, humidity, pressure]

.. note::
    This backend is a **stub** pending validation on real hardware.
    The ``measure()`` method calls the ``bme280`` library but has not
    been tested end-to-end on a physical device.
"""
from __future__ import annotations

import logging
from typing import Any

from aura_hw.backends.devices.sensor.base import SensorBackend

logger = logging.getLogger(__name__)


class BME280Backend(SensorBackend):
    """Bosch BME280 environmental sensor via I2C.

    Measures ambient temperature (°C), relative humidity (%), and
    barometric pressure (hPa).

    Parameters
    ----------
    component_id:
        Unique component identifier from ``components_config.yaml``.
    """

    def __init__(self, component_id: str) -> None:
        super().__init__(component_id)
        self._bus = None
        self._calibration = None
        self._address: int = 0x76
        self._bus_number: int = 1
        self._measurements: list[str] = ["temperature", "humidity", "pressure"]
        self._params: dict = {}

    # ── DeviceBackend interface ──────────────────────────────────────────────

    @property
    def driver(self) -> str:
        return "bme280"

    def open(self, params: dict) -> None:
        """Open the I2C bus and load BME280 calibration data.

        Args:
            params: Configuration dict with keys:

                * ``bus`` (int): I2C bus number (default 1).
                * ``address`` (str | int): I2C address in hex or decimal.
                * ``measurements`` (list[str]): Subset of measurements to
                  report (``temperature``, ``humidity``, ``pressure``).

        Raises:
            RuntimeError: If ``smbus2`` or ``bme280`` are not installed.
            OSError: If the I2C bus cannot be opened (permissions, hardware).
        """
        try:
            import smbus2  # type: ignore[import]
            import bme280 as _bme280  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                f"[{self._component_id}] BME280 backend requires 'smbus2' and "
                f"'RPi.bme280'. Install with: pip install smbus2 RPi.bme280"
            ) from exc

        self._params = params
        self._bus_number = int(params.get("bus", 1))
        addr_raw = params.get("address", "0x76")
        self._address = (
            int(addr_raw, 16) if isinstance(addr_raw, str) else int(addr_raw)
        )
        self._measurements = params.get(
            "measurements", ["temperature", "humidity", "pressure"]
        )

        self._bus = smbus2.SMBus(self._bus_number)
        self._calibration = _bme280.load_calibration_params(
            self._bus, self._address
        )
        logger.info(
            f"[{self._component_id}] BME280 opened: "
            f"bus={self._bus_number} address=0x{self._address:02X}"
        )

    def close(self) -> None:
        """Close the I2C bus."""
        if self._bus is not None:
            self._bus.close()
            self._bus = None
            logger.info(f"[{self._component_id}] BME280 closed")

    def measure(self) -> dict:
        """Read temperature, humidity and/or pressure from the sensor.

        Returns:
            Dict with the requested measurements::

                {
                    "temperature_c":  23.4,
                    "humidity_pct":   55.1,
                    "pressure_hpa": 1013.2,
                }

        Raises:
            RuntimeError: If the sensor has not been opened.
        """
        if self._bus is None or self._calibration is None:
            raise RuntimeError(
                f"[{self._component_id}] BME280 not opened. Call open() first."
            )
        import bme280 as _bme280  # type: ignore[import]

        data = _bme280.sample(self._bus, self._address, self._calibration)
        result: dict[str, float] = {}

        if "temperature" in self._measurements:
            result["temperature_c"] = round(data.temperature, 2)
        if "humidity" in self._measurements:
            result["humidity_pct"] = round(data.humidity, 2)
        if "pressure" in self._measurements:
            result["pressure_hpa"] = round(data.pressure, 2)

        logger.debug(f"[{self._component_id}] BME280 measurement: {result}")
        return result

    def info(self) -> dict:
        """Return BME280 sensor metadata."""
        result: dict[str, Any] = {
            "component_id": self._component_id,
            "device_type": self.device_type,
            "driver": self.driver,
            "status": "open" if self._bus is not None else "closed",
            "i2c_bus": self._bus_number,
            "i2c_address": f"0x{self._address:02X}",
            "measurements": self._measurements,
        }
        try:
            import bme280  # type: ignore[import]
            result["bme280_lib_version"] = getattr(bme280, "__version__", "unknown")
        except ImportError:
            pass
        return result
