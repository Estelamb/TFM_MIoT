"""AURA Hardware Shared Utilities.

Common helpers for resolving device configuration and loading dynamic drivers.
"""
import yaml
from pathlib import Path
import os
import importlib
import inspect
import logging

logger = logging.getLogger(__name__)
"""Logger instance specific to hardware driver loading."""

class MockDevice:
    """Universal mock device that responds to all method calls without crashing."""
    
    def __init__(self, *args: any, **kwargs: any):
        """Initialises the MockDevice."""
        pass
        
    def initialize(self) -> bool:
        """Mock device initialization callback.

        Returns:
            Always returns True.
        """
        return True
        
    def open(self, params: dict) -> None:
        """Mock open driver interface.

        Args:
            params: Dictionary containing configuration properties.
        """
        pass
        
    def close(self) -> None:
        """Mock close driver interface."""
        pass
        
    def read_value(self) -> dict:
        """Mock read value interface.

        Returns:
            Status metrics dictionary.
        """
        return {"status": "mock_active"}
        
    def measure(self) -> dict:
        """Mock sensor measure interface.

        Returns:
            Status metrics dictionary.
        """
        return self.read_value()
        
    def write_value(self, value: any) -> None:
        """Mock actuator write value interface.

        Args:
            value: The value payload to write.
        """
        pass
        
    def write(self, value: any) -> None:
        """Mock actuator write interface.

        Args:
            value: The value payload to write.
        """
        pass
        
    def capture_frame(self) -> any:
        """Mock camera capture frame interface.

        Returns:
            A blank 3D numpy array or list array.
        """
        try:
            import numpy as np
            return np.zeros((640, 640, 3), dtype=np.uint8)
        except ImportError:
            return [[[0, 0, 0] for _ in range(640)] for _ in range(640)]
            
    def take_photo(self) -> any:
        """Mock camera take photo interface.

        Returns:
            A blank capture frame.
        """
        return self.capture_frame()
        
    def __getattr__(self, name: str) -> callable:
        """Gracefully resolves any missing methods dynamically on the mock device.

        Args:
            name: Method name string.

        Returns:
            Callable placeholder function returning None.
        """
        def mock_method(*args, **kwargs):
            return None
        return mock_method

def get_config_path() -> Path:
    """Finds the components_config.yaml file path across standard setups.

    Returns:
        The resolved Path configuration object.
    """
    env_path = os.environ.get("AURA_COMPONENTS_CONFIG_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p.resolve()

    p = Path("/app/config/components_config.yaml")
    if p.exists():
        return p.resolve()

    p = Path(__file__).parents[1] / "edge-runtime" / "config" / "components_config.yaml"
    if p.exists():
        return p.resolve()

    p = Path("config/components_config.yaml")
    if p.exists():
        return p.resolve()

    return Path("config/components_config.yaml").resolve()

def get_active_driver(device_type: str) -> tuple[str, dict]:
    """Finds the configured driver name and params for a given device type.

    Args:
        device_type: Device classification name (e.g. 'camera', 'gps').

    Returns:
        A tuple of (driver_name, parameters_dict).
    """
    config_path = get_config_path()
    if not config_path.exists():
        logger.warning(f"components_config.yaml not found at {config_path}. Defaulting to template driver.")
        return "template", {}
    try:
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
            components = config.get("components", [])
            for c in components:
                if c.get("type") == device_type and c.get("enabled", True):
                    return c.get("driver", "template"), c.get("params", {})
    except Exception as e:
        logger.error(f"Error loading components config: {e}")
    return "template", {}

def load_specific_driver(category: str, device_type: str, driver: str) -> type:
    """Dynamically loads and returns the main class of a specific device driver.

    Args:
        category: Driver category subdirectory ('sensors', 'actuators', 'others').
        device_type: Specific target device folder name.
        driver: Target driver name.

    Returns:
        The loaded class object type, or MockDevice fallback if loading failed.
    """
    module_name = f"hardware.{category}.{device_type}.{driver.lower()}.library"
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        try:
            module = importlib.import_module(f".{driver.lower()}.library", package=f"hardware.{category}.{device_type}")
        except ImportError as e:
            logger.warning(f"Could not load specific driver library for '{driver}' under '{category}/{device_type}': {e}. Falling back to MockDevice.")
            return MockDevice
            
    classes = [obj for name, obj in inspect.getmembers(module, inspect.isclass) 
               if obj.__module__ == module_name or obj.__module__.endswith(f"{driver.lower()}.library")]
               
    if not classes:
        logger.warning(f"No class defined in driver module '{module_name}'. Falling back to MockDevice.")
        return MockDevice
        
    for cls in classes:
        cls_name = cls.__name__.lower()
        if cls_name.endswith("library") or cls_name.endswith("backend") or device_type.lower() in cls_name:
            return cls
            
    return classes[0]
