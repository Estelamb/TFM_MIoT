"""
Sensor device backends for AURA HAL.

Available backends
------------------
BME280Backend
    Bosch BME280 — temperature, humidity, pressure via I2C.
    Requires: ``smbus2``, ``RPi.bme280``
"""
from aura_hw.backends.devices.sensor.base import SensorBackend
from aura_hw.backends.devices.sensor.bme280 import BME280Backend

__all__ = ["SensorBackend", "BME280Backend"]
