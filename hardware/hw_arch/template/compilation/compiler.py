"""
Template Hardware Compiler
====================================
Use this directory as a template for adding a new compiler architecture.

To add a new compiler architecture:
  1. Copy this folder and rename it to your target architecture (e.g. `hailo10`).
  2. Implement the `compile` method in `compiler.py`.
  3. Set class attributes: `EXECUTION_STRATEGY`, `DOCKER_IMAGE`, `OUTPUT_FORMAT`, `SUPPORTED_HARDWARE`.
  4. Build/restart the docker services. The platform will automatically detect and register your compiler.

For detailed steps, execution strategies, and dataset layouts, refer to DEVELOPER_GUIDE.md.
"""
import logging
from app.compilers.base import CompilerBase, CompilationResult

logger = logging.getLogger(__name__)


LABEL = "Template Arch"

class TemplateCompiler(CompilerBase):
    EXECUTION_STRATEGY = "python"  # Choose "python" or "docker"
    DOCKER_IMAGE = ""              # If docker-based: set container image tag, e.g. "my_compiler:latest"
    OUTPUT_FORMAT = ".bin"         # Extension/format of the compiled artifact, e.g. ".hef", ".zip"
    SUPPORTED_HARDWARE = ["template"] # List of hardware identifiers supported by this compiler

    def __init__(self, minio_bucket_models: str, minio_bucket_compiled: str):
        self._bucket_models = minio_bucket_models
        self._bucket_compiled = minio_bucket_compiled

    async def compile(
        self,
        model_id: str,
        source_key: str,
        num_classes: int,
        class_names: list[str],
        hardware_type: str,
        dataset_id: str,
        dataset_key: str,
        base_architecture: str = "",
        input_size: str = "",
    ) -> CompilationResult:
        logger.info(f"[Template] Starting compilation for model {model_id}, hw={hardware_type}")

        # Example implementation steps:
        #
        # 1. Initialize MinIO client:
        #    from shared.utils.minio import get_minio
        #    minio = get_minio()
        #
        # 2. Download the source .pt model file:
        #    import tempfile
        #    with tempfile.TemporaryDirectory() as tmpdir:
        #        pt_path = os.path.join(tmpdir, "model.pt")
        #        await minio.fget_object(self._bucket_models, source_key, pt_path)
        #
        # 3. If Strategy is "python", run operations asynchronously in a thread:
        #    # await asyncio.to_thread(self._blocking_compile_fn, pt_path, ...)
        #
        # 4. If Strategy is "docker", launch compile task in a subprocess:
        #    # process = await asyncio.create_subprocess_exec("docker", "run", ...)
        #    # await process.communicate()
        #
        # 5. Upload compiled artifact back to MinIO:
        #    # compiled_key = f"{model_id}/model{self.OUTPUT_FORMAT}"
        #    # sha = await upload_bytes("compiled", compiled_key, compiled_data)
        #    # return CompilationResult(success=True, compiled_key=compiled_key, compiled_sha256=sha)
        
        return CompilationResult(
            success=False,
            error="This is a template compiler. Copy this directory to create your own compiler."
        )
