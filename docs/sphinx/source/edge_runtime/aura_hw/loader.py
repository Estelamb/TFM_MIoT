import importlib.util
import inspect
import logging
import os
import sys
import hashlib
from pathlib import Path

logger = logging.getLogger(__name__)

def get_hardware_dir() -> Path:
    """Resolve the absolute path to the root 'hardware' directory."""
    # 1. Environment variable override
    env_path = os.environ.get("AURA_HARDWARE_DIR")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p.resolve()

    # 2. Check standard docker mount /app/hardware
    p = Path("/app/hardware")
    if p.exists():
        return p.resolve()

    # 3. Check relative path from edge-runtime (inside edge-runtime/aura_hw)
    p = Path(__file__).parents[2] / "hardware"
    if p.exists():
        return p.resolve()

    # 4. Check relative to current working directory
    p = Path("hardware")
    if p.exists():
        return p.resolve()

    # Fallback
    return Path("hardware").resolve()

def load_class_from_module(module, module_name: str):
    """Utility to inspect a dynamically loaded module and find the main class."""
    classes = []
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if obj.__module__ == module_name:
            classes.append(obj)

    if not classes:
        raise AttributeError(f"No class defined in dynamically loaded module '{module_name}'")

    # Prefer classes ending in Library or Backend
    for cls in classes:
        if cls.__name__.endswith("Library") or cls.__name__.endswith("Backend"):
            return cls

    return classes[0]

def load_component_class(category: str, subcategory: str, driver: str):
    """
    Dynamically loads the library class for a custom sensor or actuator.
    Example: load_component_class("sensors", "camera", "rpi_camera_module_3")
    """
    hw_dir = get_hardware_dir()
    lib_path = hw_dir / category / subcategory / driver / "library.py"
    if not lib_path.exists():
        raise FileNotFoundError(f"Specific library not found at: {lib_path}")

    module_name = f"hardware.{category}.{subcategory}.{driver}.library"
    
    spec = importlib.util.spec_from_file_location(module_name, lib_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module spec for: {lib_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    return load_class_from_module(module, module_name)

def load_inference_class(hw: str):
    """
    Dynamically loads the inference class for a custom hardware type.
    Example: load_inference_class("test_arch") -> loaded from hardware/hw_arch/test_arch/inference/library.py
    """
    hw_dir = get_hardware_dir()
    lib_path = hw_dir / "hw_arch" / hw / "inference" / "library.py"
    if not lib_path.exists():
        raise FileNotFoundError(f"Specific inference library not found at: {lib_path}")

    module_name = f"hardware.hw_arch.{hw}.inference.library"

    spec = importlib.util.spec_from_file_location(module_name, lib_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module spec for: {lib_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    return load_class_from_module(module, module_name)

def get_libraries_hash() -> str:
    """Calculates a deterministic SHA256 hash of the local hardware directory."""
    hw_dir = get_hardware_dir()
    if not hw_dir.exists():
        return ""

    sha_hash = hashlib.sha256()
    for root, dirs, files in os.walk(hw_dir):
        dirs.sort()
        files.sort()
        for file in files:
            if "__pycache__" in root or file.endswith(".pyc") or file.endswith(".pyo"):
                continue
            file_path = Path(root) / file
            rel_path = file_path.relative_to(hw_dir)
            
            sha_hash.update(str(rel_path).encode("utf-8"))
            try:
                with open(file_path, "rb") as f:
                    for chunk in iter(lambda: f.read(65536), b""):
                        sha_hash.update(chunk)
            except OSError:
                pass
    return sha_hash.hexdigest()
