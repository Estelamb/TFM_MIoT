import random
import yaml
from pathlib import Path

class GPSSimulated:
    LABEL = "Simulated GPS"

    def __init__(self, **kwargs):
        self.coords = [-3.7038, 40.4168]  # Default fallback
        self.load_initial_coordinates()

    def load_initial_coordinates(self):
        config_dirs = [
            Path("/app/config"),
            Path(__file__).parents[4] / "edge-runtime" / "config",
            Path("config"),
            Path(".")
        ]
        for cdir in config_dirs:
            device_path = cdir / "device_config.yaml"
            if device_path.exists():
                try:
                    with open(device_path, "r", encoding="utf-8") as f:
                        cfg = yaml.safe_load(f) or {}
                        coords = cfg.get("coordinates")
                        if coords and isinstance(coords, list) and len(coords) == 2:
                            self.coords = [float(coords[0]), float(coords[1])]
                            break
                except Exception:
                    pass

    def initialize(self) -> bool:
        return True

    def read_value(self) -> list[float]:
        current = list(self.coords)
        # Add a small random drift to simulate movement (approx 1-10 meters, very small delta)
        # 0.0001 degrees is roughly 11 meters
        delta_lon = random.uniform(-0.0001, 0.0001)
        delta_lat = random.uniform(-0.0001, 0.0001)
        self.coords[0] = round(self.coords[0] + delta_lon, 6)
        self.coords[1] = round(self.coords[1] + delta_lat, 6)
        return current

    def close(self) -> None:
        pass
