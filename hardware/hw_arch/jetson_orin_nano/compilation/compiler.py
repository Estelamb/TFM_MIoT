from app.compilers.base import CompilerBase, CompilationResult

LABEL = "Jetson Orin"

class TensorRTCompiler(CompilerBase):
    EXECUTION_STRATEGY = "docker"
    DOCKER_IMAGE = ""  # TBD: Jetson container image
    OUTPUT_FORMAT = ".engine"
    SUPPORTED_HARDWARE = ["jetson_orin_nano"]

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
        return CompilationResult(
            success=False,
            error="TensorRT compiler not yet implemented."
        )
