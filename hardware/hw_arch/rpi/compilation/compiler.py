import asyncio
import logging
import os
import tempfile
import hashlib
from app.compilers.base import CompilerBase, CompilationResult
from shared.utils.minio import get_minio, upload_bytes

logger = logging.getLogger(__name__)

LABEL = "RPi (CPU)"

class RPiCPUCompiler(CompilerBase):
    EXECUTION_STRATEGY = "python"
    DOCKER_IMAGE = ""
    OUTPUT_FORMAT = ".onnx"
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
        logger.info(f"[RPiCPU] Starting compilation for model {model_id}, hw={hardware_type}")

        # Resolve image dimensions
        img_size = 640
        if input_size:
            try:
                parts = input_size.lower().split("x")
                img_size = int(parts[0])
            except Exception:
                pass

        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. Download source model (.pt) from MinIO
            pt_path = os.path.join(tmpdir, "model.pt")
            minio = get_minio()
            try:
                await minio.fget_object(self._bucket_models, source_key, pt_path)
            except Exception as e:
                return CompilationResult(success=False, error=f"Failed to download source model: {e}")

            # 2. Run graph compilation/export to ONNX in a thread executor
            try:
                onnx_tmp_path = await asyncio.to_thread(self._export_onnx, pt_path, img_size)
            except Exception as e:
                return CompilationResult(success=False, error=f"ONNX export failed: {e}")

            if not os.path.exists(onnx_tmp_path):
                return CompilationResult(success=False, error="ONNX export completed but output file not found")

            # 3. Read compiled ONNX bytes and upload to MinIO
            try:
                with open(onnx_tmp_path, "rb") as f:
                    onnx_data = f.read()
                
                sha = hashlib.sha256(onnx_data).hexdigest()
                compiled_key = f"{model_id}/model.onnx"
                
                logger.info(f"[RPiCPU] Uploading compiled model to MinIO: {compiled_key}...")
                await upload_bytes("compiled", compiled_key, onnx_data)
                
                logger.info(f"[RPiCPU] Compilation successful -> {compiled_key}")
                return CompilationResult(
                    success=True,
                    compiled_key=compiled_key,
                    compiled_sha256=sha
                )
            except Exception as e:
                return CompilationResult(success=False, error=f"Failed to process or upload compiled model: {e}")

    def _export_onnx(self, pt_path: str, img_size: int) -> str:
        from ultralytics import YOLO
        
        logger.info(f"[RPiCPU] Loading PyTorch model from {pt_path}...")
        model = YOLO(pt_path)
        
        logger.info(f"[RPiCPU] Exporting model to ONNX with imgsz={img_size}, nms=True, opset=12...")
        # Parameters matching the RPi CPU guidelines:
        # - format: "onnx"
        # - batch: 1 (edge streaming)
        # - imgsz: img_size
        # - nms: True (critical for CPU optimization)
        # - opset: 12 (stable operations matching runtime)
        # - half: False (FP32 accuracy)
        exported_path = model.export(
            format="onnx",
            imgsz=img_size,
            batch=1,
            nms=True,
            opset=12,
            half=False
        )
        return str(exported_path)

