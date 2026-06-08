"""
AURA Sensor Library: Template Sensor
=====================================
Copy this directory to add a new sensor peripheral under:
hardware/sensors/<category>/<sensor_name>/

Each sensor library must contain a class with:
1. An __init__ method accepting configuration parameters.
2. An initialize() method to set up physical connection/pins.
3. A read_value() method returning the measured value.
"""

LABEL = "Template Sensor"

class TemplateSensorLibrary:
    def __init__(self, **kwargs):
        """
        Initializes the sensor driver with the parameters defined in components_config.yaml.
        Example configuration:
          params:
            pin: 4
            address: 0x68
        """
        self.params = kwargs

    def initialize(self) -> bool:
        """
        Set up the connection to the physical sensor.
        Should perform hardware setup, verify I2C address, initialize GPIO, etc.

        Returns:
            bool: True if connection succeeded and sensor is ready, False otherwise.
        """
        # TODO: Implement connection/initialization logic
        return True

    def read_value(self) -> Any:
        """
        Read the latest value from the physical sensor.

        Returns:
            The read value. Depending on the sensor type:
            * camera -> np.ndarray (BGR frame)
            * temperature -> dict (e.g. {"temperature_celsius": 25.0})
            * distance -> float (e.g. 120.5)
            * imu -> dict (e.g. {"accel": [x, y, z], "gyro": [x, y, z]})
        """
        # TODO: Implement read logic
        return {}
