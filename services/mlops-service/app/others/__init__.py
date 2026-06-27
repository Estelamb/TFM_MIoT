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
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "LABEL":
                        return ast.literal_eval(node.value)
    except Exception:
        pass
    return None

def get_others_data() -> dict[str, str]:
    others_map = {}
    hardware_dir = get_hardware_dir()
    others_dir = hardware_dir / "others"
    if not others_dir.exists():
        return others_map
    for category in others_dir.iterdir():
        if category.is_dir() and not category.name.startswith("__"):
            # Category-level wrapper (e.g. others/template/library.py)
            cat_lib = category / "library.py"
            if cat_lib.exists():
                cat_label = get_label_from_file(cat_lib) or category.name
                others_map[category.name] = cat_label
            # Specific drivers (e.g. others/template/dummy_other/library.py)
            for item in category.iterdir():
                if item.is_dir() and not item.name.startswith("__"):
                    lib_file = item / "library.py"
                    if lib_file.exists():
                        identifier = f"{category.name}/{item.name}"
                        label = get_label_from_file(lib_file) or item.name
                        others_map[identifier] = label
    return others_map

def get_others() -> list[str]:
    """Returns only specific driver keys (e.g. 'template/dummy_other').
    Category-level keys are included in get_others_data() for label
    resolution but should not appear as selectable others in the catalog."""
    return sorted([k for k in get_others_data().keys() if "/" in k])
