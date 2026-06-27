import importlib
import pkgutil
from pathlib import Path

# Expose dynamic singletons
__all__ = []

package_dir = str(Path(__file__).parent)
for _, module_name, _ in pkgutil.iter_modules([package_dir]):
    if module_name not in ("shared",):
        module = importlib.import_module(f"daemon.{module_name}")
        for attr_name in dir(module):
            if attr_name.endswith("_manager"):
                globals()[attr_name] = getattr(module, attr_name)
                __all__.append(attr_name)
