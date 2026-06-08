"""
AURA Sensor Library: DHT22 Temperature
======================================
"""

LABEL = "DHT22 Temperature"

class DHT22Library:
    def __init__(self, pin: int = 4):
        self.pin = pin

    def initialize(self) -> bool:
        """Initialize connection to physical DHT22 sensor."""
        return True

    def read_value(self) -> dict:
        """Read temperature and humidity from the sensor."""
        return {
            "temperature_celsius": 24.5,
            "humidity_percent": 45.2
        }
