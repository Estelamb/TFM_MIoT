"""
Compilador Sony IMX500 (AI Camera)
====================================
Pipeline:
  1. Descarga el .pt desde MinIO
  2. Prepara subset de calibración (imágenes dummy para PoC)
  3. Genera YAML de calibración dinámicamente
  4. Ejecuta model.export(format="imx") via ultralytics + MCT + imx500-converter
  5. Recoge el packerOut.zip resultante
  6. Sube packerOut.zip a MinIO (bucket compiled) y devuelve CompilationResult

NOTA: requiere imx500-converter[pt] y model-compression-toolkit instalados
en el entorno. Ver Dockerfile.aicam para la imagen especializada.
"""
import asyncio
import logging
import os
import shutil
import tempfile
from pathlib import Path

from app.compilers.base import CompilerBase, CompilationResult
from shared.utils.minio import get_minio, upload_bytes

logger = logging.getLogger(__name__)


class AICamCompiler(CompilerBase):
    def __init__(self, minio_bucket_models: str, minio_bucket_compiled: str):
        self._bucket_models = minio_bucket_models
        self._bucket_compiled = minio_bucket_compiled

    async def compile(self, model_id: str, source_key: str, num_classes: int,
                      class_names: list[str], hardware_type: str) -> CompilationResult:
        logger.info(f"[AICam] Starting IMX500 compilation for model {model_id}")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            dataset_dir = tmp / "dataset"
            (dataset_dir / "images" / "train").mkdir(parents=True)
            (dataset_dir / "labels" / "train").mkdir(parents=True)

            # 1. Descargar .pt desde MinIO
            pt_path = tmp / "model.pt"
            minio = get_minio()
            try:
                await minio.fget_object(self._bucket_models, source_key, str(pt_path))
            except Exception as e:
                return CompilationResult(success=False, error=f"Failed to download model: {e}")

            # 2. Generar imágenes dummy de calibración (PoC)
            #    En producción: descargar imágenes del dataset desde MinIO
            await asyncio.to_thread(self._generate_dummy_images,
                                    str(dataset_dir / "images" / "train"), 10)

            # 3. Generar classes.txt
            classes_path = dataset_dir / "classes.txt"
            classes_path.write_text("\n".join(class_names))

            # 4. Ejecutar pipeline IMX500 en thread (bloquea CPU/GPU)
            try:
                packer_zip = await asyncio.to_thread(
                    self._run_imx_export, str(pt_path), str(dataset_dir), len(class_names))
            except Exception as e:
                return CompilationResult(success=False, error=f"IMX500 export failed: {e}")

            if not packer_zip or not Path(packer_zip).exists():
                return CompilationResult(success=False, error="packerOut.zip not found after compilation")

            # 5. Subir packerOut.zip a MinIO
            data = Path(packer_zip).read_bytes()
            compiled_key = f"{model_id}/packerOut.zip"
            sha = await upload_bytes("compiled", compiled_key, data)

            logger.info(f"[AICam] Compilation successful → {compiled_key}")
            return CompilationResult(
                success=True, compiled_key=compiled_key, compiled_sha256=sha)

    def _generate_dummy_images(self, img_dir: str, n: int) -> None:
        try:
            from PIL import Image
            for i in range(n):
                img = Image.new("RGB", (640, 640), color=(128, 128, 128))
                img.save(os.path.join(img_dir, f"img_{i:04d}.jpg"))
        except ImportError:
            pass

    def _run_imx_export(self, pt_path: str, dataset_dir: str, num_classes: int) -> str | None:
        """Ejecuta el pipeline IMX500 (síncrono, en thread)."""
        import os
        from ultralytics import YOLO
        from glob import glob

        # Preparar subset de calibración
        src_images = os.path.join(dataset_dir, "images", "train")
        calib_dir  = os.path.join(dataset_dir, "images", "calib_temp")
        calib_labels = os.path.join(dataset_dir, "labels", "calib_temp")
        os.makedirs(calib_dir, exist_ok=True)
        os.makedirs(calib_labels, exist_ok=True)

        images = glob(os.path.join(src_images, "*.jpg"))[:300]
        for img_path in images:
            shutil.copy(img_path, os.path.join(calib_dir, os.path.basename(img_path)))

        # Generar YAML dinámico
        abs_dataset = os.path.abspath(dataset_dir).replace("\\", "/")
        classes = open(os.path.join(dataset_dir, "classes.txt")).read().splitlines()
        yaml_path = os.path.join(dataset_dir, "calib.yaml")
        with open(yaml_path, "w") as f:
            f.write(f"path: {abs_dataset}\n")
            f.write("train: images/train\n")
            f.write("val: images/calib_temp\n\n")
            f.write("names:\n")
            for i, cls in enumerate(classes):
                f.write(f"  {i}: '{cls}'\n")

        # Ejecutar export
        model = YOLO(pt_path)
        model.export(format="imx", data=yaml_path)

        # Buscar packerOut.zip
        model_name = os.path.splitext(os.path.basename(pt_path))[0]
        model_dir  = os.path.dirname(pt_path)
        packer_zip = os.path.join(model_dir, f"{model_name}_imx_model", "packerOut.zip")

        # Cleanup
        shutil.rmtree(calib_dir, ignore_errors=True)
        shutil.rmtree(calib_labels, ignore_errors=True)
        if os.path.exists(yaml_path):
            os.remove(yaml_path)

        return packer_zip if os.path.exists(packer_zip) else None
