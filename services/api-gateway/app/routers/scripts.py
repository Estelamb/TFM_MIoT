import ast
import uuid
import logging
import aiohttp
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, UploadFile
from app.auth.jwt import verify_token
from app.stubs import get_stub
from shared.proto_gen import script_pb2
from shared.utils.minio import upload_bytes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scripts", tags=["scripts"])

@router.post("", status_code=201)
async def upload_script(
    name: str = Form(...), description: str = Form(""),
    language: str = Form("python"),
    file: UploadFile = File(...), _=Depends(verify_token),
):
    data = await file.read()
    script_id = str(uuid.uuid4())
    original_ext = file.filename.split('.')[-1] if file.filename and '.' in file.filename else "py"
    script_key = f"{script_id}/script.{original_ext}"
    sha = await upload_bytes("scripts", script_key, data)
    sc = await get_stub("script").UploadScript(script_pb2.UploadScriptRequest(
        name=name, description=description, language=language,
        script_key=script_key, script_sha256=sha))
    return {"id": sc.id, "name": sc.name, "language": sc.language, "created_at": sc.created_at}

@router.get("")
async def list_scripts(_=Depends(verify_token)):
    r = await get_stub("script").ListScripts(script_pb2.ListScriptsRequest())
    from shared.utils.minio import get_minio
    from app.config import get_settings
    s_settings = get_settings()
    minio = get_minio()
    
    scripts_list = []
    async with aiohttp.ClientSession() as session:
        for s in r.scripts:
            content = ""
            if s.script_key:
                try:
                    resp = await minio.get_object(s_settings.minio_bucket_scripts, s.script_key, session)
                    content_bytes = await resp.read()
                    content = content_bytes.decode("utf-8")
                except Exception as e:
                    logger.error(f"Error fetching script content for {s.script_key}: {e}")
            scripts_list.append({
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "language": s.language,
                "script_sha256": s.script_sha256,
                "created_at": s.created_at,
                "content": content
            })
    return scripts_list


# ── Hardware Libraries API ────────────────────────────────────────────────────

def _get_hardware_dir() -> Path:
    """Resolve hardware/ directory path."""
    for candidate in [
        Path("/app/hardware"),
        Path(__file__).parents[3] / "hardware",
        Path("hardware"),
    ]:
        if candidate.exists():
            return candidate.resolve()
    return Path("hardware").resolve()


def _extract_library_api(library_path: Path) -> list[dict]:
    """Parse a library.py file and extract class methods + module-level functions
    with their signatures and docstrings."""
    try:
        source = library_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except Exception as exc:
        logger.warning(f"Could not parse {library_path}: {exc}")
        return []

    entries: list[dict] = []
    module_doc = ast.get_docstring(tree)

    for node in ast.iter_child_nodes(tree):
        # Extract class methods
        if isinstance(node, ast.ClassDef):
            class_name = node.name
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if item.name.startswith("_"):
                        continue
                    sig = _build_signature(item)
                    doc = ast.get_docstring(item) or ""
                    entries.append({
                        "name": f"{class_name}.{item.name}({sig})",
                        "desc": doc,
                        "type": "method",
                    })

        # Extract module-level functions
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue
            sig = _build_signature(node)
            doc = ast.get_docstring(node) or ""
            entries.append({
                "name": f"{node.name}({sig})",
                "desc": doc,
                "type": "function",
            })

    return entries


def _build_signature(func_node: ast.FunctionDef) -> str:
    """Build a human-readable signature string from an AST function node."""
    args = func_node.args
    parts: list[str] = []

    # positional args (skip 'self')
    all_args = args.args
    defaults = args.defaults
    n_defaults = len(defaults)
    n_args = len(all_args)

    for i, arg in enumerate(all_args):
        if arg.arg == "self":
            continue
        name = arg.arg
        # Type annotation
        if arg.annotation:
            try:
                name += f": {ast.unparse(arg.annotation)}"
            except Exception:
                pass
        # Default value
        default_idx = i - (n_args - n_defaults)
        if default_idx >= 0:
            try:
                name += f" = {ast.unparse(defaults[default_idx])}"
            except Exception:
                pass
        parts.append(name)

    # **kwargs
    if args.kwarg:
        parts.append(f"**{args.kwarg.arg}")

    return ", ".join(parts)


def _compute_import_path(hw_dir: Path, lib_path: Path) -> str:
    """Compute the Python import path like 'hardware.sensors.camera.library'."""
    try:
        rel = lib_path.relative_to(hw_dir.parent)
        return str(rel.with_suffix("")).replace("/", ".").replace("\\", ".")
    except ValueError:
        return str(lib_path)


@router.get("/libraries")
async def list_libraries(_=Depends(verify_token)):
    """Scan the hardware/ directory and return the generic library APIs.

    Returns a dict mapping category to a list of API entries extracted
    from each library.py file.
    """
    hw_dir = _get_hardware_dir()
    if not hw_dir.exists():
        return {"libraries": []}

    libraries: list[dict] = []

    # Scan sensors/, actuators/, others/
    for category in ("sensors", "actuators", "others"):
        cat_dir = hw_dir / category
        if not cat_dir.is_dir():
            continue
        for subcategory_dir in sorted(cat_dir.iterdir()):
            if not subcategory_dir.is_dir() or subcategory_dir.name.startswith("_"):
                continue
            if subcategory_dir.name == "template":
                continue
            lib_file = subcategory_dir / "library.py"
            if not lib_file.exists():
                continue
            import_path = _compute_import_path(hw_dir, lib_file)
            api_entries = _extract_library_api(lib_file)
            libraries.append({
                "category": category,
                "subcategory": subcategory_dir.name,
                "import_path": import_path,
                "api": api_entries,
            })

    # Add generic Inference Library (aura_hw) instead of architecture-specific ones
    libraries.append({
        "category": "hw_arch",
        "subcategory": "Inference Library",
        "import_path": "aura_hw",
        "api": [
            {
                "name": "load_model(model_path: str)",
                "desc": "Detect hardware and load a compiled model.",
                "type": "function"
            },
            {
                "name": "execute_inference(inputs: np.ndarray | dict | None = None)",
                "desc": "Run a single inference pass with the currently loaded model.",
                "type": "function"
            },
            {
                "name": "unload_model()",
                "desc": "Unload the current model and release accelerator resources.",
                "type": "function"
            },
            {
                "name": "get_hardware_info()",
                "desc": "Return a snapshot of the current hardware and model state (hardware_type, model_loaded, backend, device_info).",
                "type": "function"
            },
            {
                "name": "get_last_inference()",
                "desc": "Return the result of the most recent execute_inference call.",
                "type": "function"
            }
        ]
    })

    return {"libraries": libraries}


@router.get("/{script_id}")
async def get_script(script_id: str, _=Depends(verify_token)):
    s = await get_stub("script").GetScript(script_pb2.GetScriptRequest(id=script_id))
    from shared.utils.minio import get_minio
    from app.config import get_settings
    s_settings = get_settings()
    minio = get_minio()
    
    content = ""
    if s.script_key:
        try:
            async with aiohttp.ClientSession() as session:
                resp = await minio.get_object(s_settings.minio_bucket_scripts, s.script_key, session)
                content_bytes = await resp.read()
                content = content_bytes.decode("utf-8")
        except Exception as e:
            logger.error(f"Error fetching script content for {s.script_key}: {e}")
            
    return {
        "id": s.id,
        "name": s.name,
        "description": s.description,
        "language": s.language,
        "script_sha256": s.script_sha256,
        "created_at": s.created_at,
        "content": content
    }

@router.delete("/{script_id}", status_code=204)
async def delete_script(script_id: str, _=Depends(verify_token)):
    await get_stub("script").DeleteScript(script_pb2.DeleteScriptRequest(id=script_id))

