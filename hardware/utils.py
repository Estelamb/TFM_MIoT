"""
AURA Hardware Shared Utilities
==============================
Common helpers for resolving device configuration and loading dynamic drivers.
"""
import yaml
from pathlib import Path
import os
import importlib
import inspect
import logging

logger = logging.getLogger(__name__)

class MockDevice:
    """Universal mock device that responds to all method calls without crashing."""
    def __init__(self, *args, **kwargs):
        pass
    def initialize(self) -> bool:
        return True
    def open(self, params: dict) -> None:
        pass
    def close(self) -> None:
        pass
    def read_value(self):
        return {"status": "mock_active"}
    def measure(self):
        return self.read_value()
    def write_value(self, value) -> None:
        pass
    def write(self, value) -> None:
        pass
    def capture_frame(self):
        try:
            import numpy as np
            return np.zeros((640, 640, 3), dtype=np.uint8)
        except ImportError:
            return [[[0, 0, 0] for _ in range(640)] for _ in range(640)]
    def take_photo(self):
        return self.capture_frame()
    def __getattr__(self, name):
        # Gracefully handle any other dynamic methods
        def mock_method(*args, **kwargs):
            return None
        return mock_method

def get_config_path() -> Path:
    """Find the components_config.yaml file path across standard setups."""
    env_path = os.environ.get("AURA_COMPONENTS_CONFIG_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p.resolve()

    # Standard docker mount
    p = Path("/app/config/components_config.yaml")
    if p.exists():
        return p.resolve()

    # Workspace sibling check relative to this file
    p = Path(__file__).parents[1] / "edge-runtime" / "config" / "components_config.yaml"
    if p.exists():
        return p.resolve()

    # Relative to current working directory
    p = Path("config/components_config.yaml")
    if p.exists():
        return p.resolve()

    return Path("config/components_config.yaml").resolve()

def get_active_driver(device_type: str) -> tuple[str, dict]:
    """Find the configured driver name and params for a given device type."""
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
    """Dynamically load and return the main class of a specific device driver."""
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
