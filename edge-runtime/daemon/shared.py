import logging
import os
import sys
from pathlib import Path
from typing import Any

# Setup logger for imported use
logger = logging.getLogger("hardware_daemon")

# Try to import Pillow (PIL) for fallback simulation
try:
    from PIL import Image, ImageDraw
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

# Fallback minimal 1x1 black JPEG image bytes in case Pillow is missing
MINIMAL_JPEG = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00\x37\xff\xd9'


def load_config() -> tuple[str, bool]:
    """Resolves the hardware_type and whether the camera is enabled.
    Looks in: env vars > config/components_config.yaml > defaults.
    """
    import yaml
    
    # 1. Resolve hardware_type from env var, defaulting to rpi
    hw_type = os.environ.get("AURA_HARDWARE_TYPE")
    if not hw_type or hw_type.lower() == "auto":
        hw_type = "rpi"  # Default fallback, no physical auto-probing
    else:
        hw_type = hw_type.lower()

    # 2. Resolve camera enabled state based on AURA_PERIPHERALS (if defined) or YAML
    peripherals_env = os.environ.get("AURA_PERIPHERALS")
    active_peripherals = None
    if peripherals_env:
        try:
            import json
            if peripherals_env.strip().startswith("["):
                active_peripherals = set(json.loads(peripherals_env))
            else:
                active_peripherals = set(p.strip() for p in peripherals_env.split(",") if p.strip())
        except Exception:
            pass

    camera_enabled = False
    config_dirs = [
        Path(__file__).parents[1] / "config",
        Path("/app/config"),
        Path("./config"),
        Path(".")
    ]
    for cdir in config_dirs:
        comp_path = cdir / "components_config.yaml"
        if comp_path.exists():
            try:
                with open(comp_path, "r", encoding="utf-8") as f:
                    comp_cfg = yaml.safe_load(f) or {}
                    components = comp_cfg.get("components", [])
                    for comp in components:
                        if comp.get("type") == "camera":
                            comp_id = comp.get("id")
                            if active_peripherals is not None:
                                if comp_id in active_peripherals:
                                    camera_enabled = True
                                    break
                            else:
                                if comp.get("enabled", True):
                                    camera_enabled = True
                                    break
            except Exception:
                pass
            break

    return hw_type, camera_enabled


HARDWARE_TYPE, CAMERA_ENABLED = load_config()


def _make_json_serializable(val: Any) -> Any:
    import numpy as np
    if isinstance(val, np.ndarray):
        return val.tolist()
    if isinstance(val, dict):
        return {k: _make_json_serializable(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [_make_json_serializable(v) for v in val]
    if isinstance(val, (np.integer, np.floating)):
        return val.item()
    return val
