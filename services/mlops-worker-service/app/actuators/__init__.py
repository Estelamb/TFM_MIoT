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

def get_actuators_data() -> dict[str, str]:
    actuators_map = {}
    hardware_dir = get_hardware_dir()
    actuators_dir = hardware_dir / "actuators"
    if not actuators_dir.exists():
        return actuators_map
    for category in actuators_dir.iterdir():
        if category.is_dir() and not category.name.startswith("__"):
            for item in category.iterdir():
                if item.is_dir() and not item.name.startswith("__"):
                    lib_file = item / "library.py"
                    if lib_file.exists():
                        identifier = f"{category.name}/{item.name}"
                        label = get_label_from_file(lib_file) or item.name
                        actuators_map[identifier] = label
    return actuators_map

def get_actuators() -> list[str]:
    return sorted(list(get_actuators_data().keys()))
