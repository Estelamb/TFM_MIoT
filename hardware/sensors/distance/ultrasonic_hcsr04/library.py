"""
AURA Sensor Library: Ultrasonic HC-SR04
=======================================
"""

LABEL = "Ultrasonic HC-SR04"

class HCSR04Library:
    def __init__(self, trigger_pin: int = 23, echo_pin: int = 24):
        self.trigger = trigger_pin
        self.echo = echo_pin

    def initialize(self) -> bool:
        """Initialize the ultrasonic sensor pins."""
        return True

    def read_value(self) -> float:
        """Measure distance in centimeters."""
        return 120.5
