from pathlib import Path
import ast

def get_hardware_dir() -> Path:
    p = Path("/app/hardware")
    if p.exists():
        return p
    return Path(__file__).parents[4] / "hardware"

def get_label_from_file(file_path: Path) -> str | None:
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "LABEL":
                        return ast.literal_eval(node.value)
    except Exception:
        pass
    return None

def get_sensors_data() -> dict[str, str]:
    sensors_map = {}
    hardware_dir = get_hardware_dir()
    sensors_dir = hardware_dir / "sensors"
    if not sensors_dir.exists():
        return sensors_map
    for category in sensors_dir.iterdir():
        if category.is_dir() and not category.name.startswith("__"):
            for item in category.iterdir():
                if item.is_dir() and not item.name.startswith("__"):
                    lib_file = item / "library.py"
                    if lib_file.exists():
                        identifier = f"{category.name}/{item.name}"
                        label = get_label_from_file(lib_file) or item.name
                        sensors_map[identifier] = label
    return sensors_map

def get_sensors() -> list[str]:
    return sorted(list(get_sensors_data().keys()))
