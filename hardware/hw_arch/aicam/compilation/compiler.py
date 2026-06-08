"""
Compilador Sony IMX500 (AI Camera)
====================================
Pipeline:
  1. Descarga el .pt desde MinIO
  2. Prepara subset de calibración real (desde el zip del dataset) o dummy
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


LABEL = "RPi AI Cam"

class AICamCompiler(CompilerBase):
    EXECUTION_STRATEGY = "python"
    DOCKER_IMAGE = ""
    OUTPUT_FORMAT = ".zip"
    SUPPORTED_HARDWARE = ["rpi_ai_cam", "aicam"]

    def __init__(self, minio_bucket_models: str, minio_bucket_compiled: str):
        self._bucket_models = minio_bucket_models
        self._bucket_compiled = minio_bucket_compiled

    async def compile(self, model_id: str, source_key: str, num_classes: int,
                      class_names: list[str], hardware_type: str,
                      dataset_id: str, dataset_key: str,
                      base_architecture: str = "", input_size: str = "") -> CompilationResult:
        logger.info(f"[AICam] Starting IMX500 compilation for model {model_id}")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            # 1. Descargar .pt desde MinIO
            pt_path = tmp / "model.pt"
            minio = get_minio()
            try:
                await minio.fget_object(self._bucket_models, source_key, str(pt_path))
            except Exception as e:
                return CompilationResult(success=False, error=f"Failed to download model: {e}")

            w, h = 640, 640
            if input_size:
                try:
                    w_str, h_str = input_size.lower().split("x")
                    w, h = int(w_str), int(h_str)
                except Exception:
                    pass

            dataset_zip_path = None
            if dataset_key:
                try:
                    dataset_zip_path = tmp / "dataset.zip"
                    logger.info(f"[AICam] Downloading dataset zip from datasets/{dataset_key}...")
                    await minio.fget_object("datasets", dataset_key, str(dataset_zip_path))
                except Exception as e:
                    logger.warning(f"[AICam] Failed to download dataset zip: {e}. Falling back to dummy images.")
                    dataset_zip_path = None
            else:
                logger.warning("[AICam] No dataset_key provided. Falling back to dummy images.")

            redis = getattr(self, "redis_client", None)
            cancel_key = f"cancel:compile:{model_id}"

            if redis and await redis.exists(cancel_key):
                raise asyncio.CancelledError()

            # Run calibration setup and IMX export in a background thread
            try:
                packer_zip = await asyncio.to_thread(
                    self._run_imx_export,
                    str(pt_path),
                    str(tmp),
                    dataset_zip_path,
                    class_names,
                    (w, h)
                )
            except Exception as e:
                return CompilationResult(success=False, error=f"IMX500 export failed: {e}")

            if redis and await redis.exists(cancel_key):
                raise asyncio.CancelledError()

            if not packer_zip or not Path(packer_zip).exists():
                return CompilationResult(success=False, error="packerOut.zip not found after compilation")

            # 5. Subir packerOut.zip a MinIO
            data = await asyncio.to_thread(Path(packer_zip).read_bytes)
            compiled_key = f"{model_id}/packerOut.zip"
            sha = await upload_bytes("compiled", compiled_key, data)

            logger.info(f"[AICam] Compilation successful → {compiled_key}")
            return CompilationResult(
                success=True, compiled_key=compiled_key, compiled_sha256=sha)

    def _generate_dummy_images_sync(self, img_dir: str, label_dir: str, n: int, size: tuple[int, int]) -> None:
        try:
            from PIL import Image
            for i in range(n):
                img = Image.new("RGB", size, color=(128, 128, 128))
                img_name = f"img_{i:04d}.jpg"
                img.save(os.path.join(img_dir, img_name))
                
                # Write dummy labels so it doesn't crash on validation split check
                label_name = f"img_{i:04d}.txt"
                with open(os.path.join(label_dir, label_name), "w") as f:
                    f.write("0 0.5 0.5 1.0 1.0\n")
        except Exception as e:
            logger.error(f"[AICam] Failed to generate dummy calibration data: {e}")

    def _run_imx_export(
        self,
        pt_path: str,
        tmp_dir: str,
        dataset_zip_path: Path | None,
        class_names: list[str],
        size: tuple[int, int]
    ) -> str | None:
        """Runs the IMX500 calibration and export pipeline (blocking, runs in thread)."""
        import os
        import shutil
        import zipfile
        from glob import glob
        from ultralytics import YOLO

        tmp = Path(tmp_dir)
        dataset_dir = tmp / "dataset"
        dataset_dir.mkdir(parents=True, exist_ok=True)
        
        train_images_dir = dataset_dir / "images" / "train"
        train_labels_dir = dataset_dir / "labels" / "train"
        train_images_dir.mkdir(parents=True, exist_ok=True)
        train_labels_dir.mkdir(parents=True, exist_ok=True)

        calib_dir = dataset_dir / "images" / "calib_temp"
        calib_labels = dataset_dir / "labels" / "calib_temp"
        
        yaml_path = dataset_dir / "calib.yaml"
        
        try:
            dataset_extracted = False
            if dataset_zip_path and dataset_zip_path.exists():
                try:
                    # Extract zip
                    extract_dir = tmp / "extracted_dataset"
                    extract_dir.mkdir(parents=True, exist_ok=True)
                    with zipfile.ZipFile(dataset_zip_path, 'r') as zip_ref:
                        zip_ref.extractall(extract_dir)
                        
                    # Find all images recursively
                    all_images = []
                    for root, dirs, files in os.walk(extract_dir):
                        for f in files:
                            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                                all_images.append(Path(root) / f)

                    # Find all label files and map their basename to their path
                    label_map = {}
                    for root, dirs, files in os.walk(extract_dir):
                        for f in files:
                            if f.lower().endswith('.txt'):
                                label_map[f.lower()] = Path(root) / f

                    # Copy files
                    for img_path in all_images:
                        shutil.copy(img_path, train_images_dir / img_path.name)
                        label_name = img_path.with_suffix(".txt").name.lower()
                        if label_name in label_map:
                            shutil.copy(label_map[label_name], train_labels_dir / img_path.with_suffix(".txt").name)
                                
                    # Verify we got some images
                    if any(train_images_dir.iterdir()):
                        dataset_extracted = True
                    else:
                        logger.warning("[AICam] Extracted dataset contains no images. Falling back to dummy images.")
                except Exception as e:
                    logger.warning(f"[AICam] Failed to extract dataset zip: {e}. Falling back to dummy images.")

            if not dataset_extracted:
                logger.info("[AICam] Generating dummy images and label files for calibration...")
                self._generate_dummy_images_sync(str(train_images_dir), str(train_labels_dir), 10, size)

            # Preparar subset de calibración (up to 300 images)
            os.makedirs(calib_dir, exist_ok=True)
            os.makedirs(calib_labels, exist_ok=True)

            images = glob(os.path.join(train_images_dir, "*.jpg")) + \
                     glob(os.path.join(train_images_dir, "*.jpeg")) + \
                     glob(os.path.join(train_images_dir, "*.png"))
            images = images[:300]
            
            for img_path in images:
                basename = os.path.basename(img_path)
                shutil.copy(img_path, os.path.join(calib_dir, basename))

                label_name = os.path.splitext(basename)[0] + ".txt"
                label_src = os.path.join(train_labels_dir, label_name)
                if os.path.exists(label_src):
                    shutil.copy(label_src, os.path.join(calib_labels, label_name))

            # Generar YAML dinámico
            abs_dataset = os.path.abspath(dataset_dir).replace("\\", "/")
            with open(yaml_path, "w", encoding="utf-8") as f:
                f.write(f"path: {abs_dataset}\n")
                f.write("train: images/train\n")
                f.write("val: images/calib_temp\n\n")
                f.write("names:\n")
                for i, cls in enumerate(class_names):
                    f.write(f"  {i}: '{cls}'\n")

            # Ejecutar export
            model = YOLO(pt_path)
            model.export(format="imx", data=str(yaml_path))

            # Buscar packerOut.zip
            model_name = os.path.splitext(os.path.basename(pt_path))[0]
            model_dir = os.path.dirname(pt_path)
            packer_zip = os.path.join(model_dir, f"{model_name}_imx_model", "packerOut.zip")
            
            return packer_zip if os.path.exists(packer_zip) else None

        finally:
            # Clean up temp files
            shutil.rmtree(calib_dir, ignore_errors=True)
            shutil.rmtree(calib_labels, ignore_errors=True)
            if os.path.exists(yaml_path):
                os.remove(yaml_path)
