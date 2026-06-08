"""
AURA Actuator Library: Standard Servo SG90
==========================================
"""

LABEL = "Standard Servo SG90"

class ServoSG90Library:
    def __init__(self, pin: int = 12):
        self.pin = pin

    def initialize(self) -> bool:
        """Initialize the servo PWM pin."""
        return True

    def write_value(self, angle: float):
        """Set the servo arm angle (0 to 180 degrees)."""
        pass
