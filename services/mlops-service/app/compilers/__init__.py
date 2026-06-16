import importlib.util
import inspect
import logging
import sys
import ast
from pathlib import Path
from app.compilers.base import CompilerBase

logger = logging.getLogger(__name__)

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

def discover_compilers(minio_bucket_models: str, minio_bucket_compiled: str) -> dict:
    registry = {}
    hardware_dir = get_hardware_dir()
    hw_arch_dir = hardware_dir / "hw_arch"
    
    if not hw_arch_dir.exists():
        logger.warning(f"Hardware architectures directory does not exist: {hw_arch_dir}")
        return registry
    
    # Iterate over all subdirectories under hw_arch_dir
    for item in hw_arch_dir.iterdir():
        if item.is_dir() and not item.name.startswith("__"):
            compiler_file = item / "compilation" / "compiler.py"
            if not compiler_file.exists():
                continue
                
            module_name = f"hardware.hw_arch.{item.name}.compilation.compiler"
            try:
                spec = importlib.util.spec_from_file_location(module_name, str(compiler_file))
                if spec is None or spec.loader is None:
                    raise ImportError(f"Could not load spec for {compiler_file}")
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                
                # Find all classes that inherit from CompilerBase (excluding CompilerBase itself)
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, CompilerBase) and obj is not CompilerBase:
                        # Instantiate the compiler
                        instance = obj(minio_bucket_models, minio_bucket_compiled)
                        # Register by folder name
                        registry[item.name] = instance
                        # Register by any other hardware types supported by the compiler
                        for hw in getattr(instance, "SUPPORTED_HARDWARE", []):
                            registry[hw] = instance
                        logger.info(f"Loaded compiler for architecture '{item.name}' from {compiler_file}")
            except Exception as e:
                logger.error(f"Failed to load compiler from {compiler_file}: {e}", exc_info=True)
                
    return registry

def get_architectures_data() -> dict[str, str]:
    data = {}
    hardware_dir = get_hardware_dir()
    hw_arch_dir = hardware_dir / "hw_arch"
    if not hw_arch_dir.exists():
        return data
    for item in hw_arch_dir.iterdir():
        if item.is_dir() and not item.name.startswith("__"):
            compiler_file = item / "compilation" / "compiler.py"
            if compiler_file.exists():
                label = get_label_from_file(compiler_file) or item.name
                data[item.name] = label
    return data

def get_architectures() -> list[str]:
    return sorted(list(get_architectures_data().keys()))
