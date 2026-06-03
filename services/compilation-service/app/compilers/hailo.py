"""
Compilador Hailo-8 / Hailo-8L
==============================
Pipeline:
  1. Descarga el .pt desde MinIO
  2. Exporta a ONNX (nms=False, opset=11, batch=1) via hailo_pipeline logic
  3. Genera directorio de calibración (1024 imágenes centre-crop 640x640)
     Las imágenes de calibración vienen del bucket MinIO del dataset, o se
     usan las que vengan con el modelo. Para PoC usamos imágenes dummy si
     no hay dataset disponible.
  4. Lanza el contenedor Docker de Hailo AI SW Suite con los assets montados
  5. Espera a que el contenedor termine y recoge el .hef resultante
  6. Sube el .hef a MinIO (bucket compiled) y devuelve CompilationResult
"""
import asyncio
import hashlib
import io
import logging
import os
import tempfile
from pathlib import Path

from app.compilers.base import CompilerBase, CompilationResult
from shared.utils.minio import get_minio, upload_bytes

logger = logging.getLogger(__name__)

HAILO_DOCKER_IMAGE = os.environ.get("HAILO_DOCKER_IMAGE", "hailo_ai_sw_suite:latest")
HAILO_MODEL_ZOO_YAML = "workspace/hailo_model_zoo/hailo_model_zoo/cfg/networks/yolov8n.yaml"


class HailoCompiler(CompilerBase):
    def __init__(self, minio_bucket_models: str, minio_bucket_compiled: str):
        self._bucket_models = minio_bucket_models
        self._bucket_compiled = minio_bucket_compiled

    async def compile(self, model_id: str, source_key: str, num_classes: int,
                      class_names: list[str], hardware_type: str,
                      dataset_version_id: str, dataset_key: str) -> CompilationResult:
        logger.info(f"[Hailo] Starting compilation for model {model_id}, hw={hardware_type}")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            shared_dir = tmp / "shared_with_docker"
            shared_dir.mkdir()

            # 1. Descargar .pt desde MinIO
            pt_path = tmp / "model.pt"
            minio = get_minio()
            try:
                await minio.fget_object(self._bucket_models, source_key, str(pt_path))
            except Exception as e:
                return CompilationResult(success=False, error=f"Failed to download model: {e}")

            # 2. Exportar a ONNX (hailo_pipeline logic integrada aquí)
            onnx_path = tmp / "model.onnx"
            try:
                await asyncio.to_thread(self._export_onnx, str(pt_path), str(onnx_path))
            except Exception as e:
                return CompilationResult(success=False, error=f"ONNX export failed: {e}")

            # 3. Copiar onnx al shared dir
            import shutil
            shutil.copy(onnx_path, shared_dir / "model.onnx")
            calib_dir = shared_dir / "calib"
            calib_dir.mkdir()
            # Para PoC: imágenes dummy de calibración (1x640x640 negro)
            # Cuando haya dataset real, descargar desde MinIO
            await asyncio.to_thread(self._generate_dummy_calib, str(calib_dir), 8)

            # 4. Lanzar Hailo Docker
            hef_path = shared_dir / "model.hef"
            docker_cmd = [
                "docker", "run", "--rm",
                "-v", f"{shared_dir}:/shared_with_docker",
                HAILO_DOCKER_IMAGE,
                "bash", "-c",
                f"cd / && hailomz compile "
                f"--ckpt /shared_with_docker/model.onnx "
                f"--calib-path /shared_with_docker/calib "
                f"--yaml {HAILO_MODEL_ZOO_YAML} "
                f"--classes {num_classes} "
                f"--hw-arch {hardware_type} "
                f"--output-dir /shared_with_docker"
            ]
            try:
                proc = await asyncio.create_subprocess_exec(
                    *docker_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                if proc.returncode != 0:
                    err = stderr.decode()[-2000:]
                    logger.error(f"[Hailo] Docker compilation failed:\n{err}")
                    return CompilationResult(success=False, error=f"hailomz compile failed: {err}")
            except FileNotFoundError:
                return CompilationResult(success=False, error="Docker not found on host")

            # 5. Buscar .hef generado
            hef_files = list(shared_dir.glob("*.hef"))
            if not hef_files:
                return CompilationResult(success=False, error="No .hef found after compilation")
            hef_path = hef_files[0]

            # 6. Subir .hef a MinIO
            hef_data = hef_path.read_bytes()
            compiled_key = f"{model_id}/model.hef"
            sha = await upload_bytes("compiled", compiled_key, hef_data)

            logger.info(f"[Hailo] Compilation successful → {compiled_key}")
            return CompilationResult(
                success=True, compiled_key=compiled_key, compiled_sha256=sha)

    def _export_onnx(self, pt_path: str, onnx_path: str) -> None:
        from ultralytics import YOLO
        model = YOLO(pt_path)
        exported = model.export(format="onnx", batch=1, nms=False, opset=11)
        import shutil
        shutil.move(str(exported), onnx_path)

    def _generate_dummy_calib(self, calib_dir: str, n: int) -> None:
        """Genera imágenes negras 640x640 para calibración mínima en PoC."""
        try:
            from PIL import Image
            for i in range(n):
                img = Image.new("RGB", (640, 640), color=(0, 0, 0))
                img.save(os.path.join(calib_dir, f"calib_{i}.jpg"))
        except ImportError:
            # Fallback: escribir JPEG mínimo válido
            import struct
            for i in range(n):
                path = os.path.join(calib_dir, f"calib_{i}.jpg")
                open(path, "wb").write(b"\xff\xd8\xff\xd9")  # minimal JPEG
