from app.compilers.base import CompilerBase, CompilationResult

LABEL = "RPi (CPU)"

class TFLiteCompiler(CompilerBase):
    EXECUTION_STRATEGY = "python"
    DOCKER_IMAGE = ""
    OUTPUT_FORMAT = ".tflite"
    SUPPORTED_HARDWARE = ["rpi"]

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
            error="TFLite compiler not yet implemented. Use model.export(format='tflite') via Ultralytics."
        )
