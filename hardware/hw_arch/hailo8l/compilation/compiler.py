"""
Compilador Hailo-8L
==============================
Pipeline:
  1. Descarga el .pt desde MinIO
  2. Exporta a ONNX (nms=False, opset=11, batch=1) via hailo_pipeline logic
  3. Genera directorio de calibración (1024 imágenes centre-crop 640x640)
  4. Lanza el contenedor Docker de Hailo AI SW Suite con los assets montados
  5. Espera a que el contenedor termine y recoge el .hef resultante
  6. Sube el .hef a MinIO (bucket compiled) y devuelve CompilationResult
"""
import asyncio
import logging
import os
import tempfile
from pathlib import Path

from app.compilers.base import CompilerBase, CompilationResult
from shared.utils.minio import get_minio, upload_bytes

logger = logging.getLogger(__name__)

HAILO_DOCKER_IMAGE = os.environ.get("HAILO_DOCKER_IMAGE", "hailo_ai_sw_suite:latest")


LABEL = "Hailo-8L"

class Hailo8LCompiler(CompilerBase):
    EXECUTION_STRATEGY = "docker"
    DOCKER_IMAGE = HAILO_DOCKER_IMAGE
    OUTPUT_FORMAT = ".hef"
    SUPPORTED_HARDWARE = ["hailo8l"]

    def __init__(self, minio_bucket_models: str, minio_bucket_compiled: str):
        self._bucket_models = minio_bucket_models
        self._bucket_compiled = minio_bucket_compiled

    async def compile(self, model_id: str, source_key: str, num_classes: int,
                      class_names: list[str], hardware_type: str,
                      dataset_id: str, dataset_key: str,
                      base_architecture: str = "", input_size: str = "") -> CompilationResult:
        logger.info(f"[Hailo8L] Starting compilation for model {model_id}, hw={hardware_type}")

        # Resolve dynamic base model configuration
        base_arch = base_architecture.strip() if base_architecture else "yolov8n.pt"
        if base_arch.endswith(".pt"):
            base_arch = base_arch[:-3]
        if not base_arch.endswith(".yaml"):
            base_arch = f"{base_arch}.yaml"
        yaml_path = f"workspace/hailo_model_zoo/hailo_model_zoo/cfg/networks/{base_arch}"

        # Resolve image dimensions for calibration
        w, h = 640, 640
        if input_size:
            try:
                w_str, h_str = input_size.lower().split("x")
                w, h = int(w_str), int(h_str)
            except Exception:
                pass

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

            # Prepare calibration images
            dataset_prepared = False
            if dataset_key:
                try:
                    # Download dataset zip
                    zip_path = tmp / "dataset.zip"
                    logger.info(f"[Hailo8L] Downloading dataset zip from datasets/{dataset_key}...")
                    await minio.fget_object("datasets", dataset_key, str(zip_path))
                    
                    # Extract dataset zip
                    extract_dir = tmp / "dataset"
                    extract_dir.mkdir()
                    
                    def _extract_zip(zpath, edir):
                        import zipfile
                        with zipfile.ZipFile(zpath, 'r') as zip_ref:
                            zip_ref.extractall(edir)
                            
                    logger.info(f"[Hailo8L] Extracting dataset zip...")
                    await asyncio.to_thread(_extract_zip, str(zip_path), str(extract_dir))
                    
                    # Prepare calibration images
                    logger.info(f"[Hailo8L] Preparing calibration images...")
                    valid_count = await asyncio.to_thread(
                        self._prepare_calibration_images,
                        extract_dir,
                        calib_dir,
                        (w, h),
                        1024
                    )
                    if valid_count > 0:
                        dataset_prepared = True
                        logger.info(f"[Hailo8L] Prepared {valid_count} calibration images from dataset.")
                    else:
                        logger.warning("[Hailo8L] No valid images were successfully processed from the dataset. Falling back to dummy images.")
                except Exception as e:
                    logger.warning(f"[Hailo8L] Failed to prepare calibration images from dataset: {e}. Falling back to dummy images.")
            else:
                logger.warning("[Hailo8L] dataset_key is empty or not provided. Falling back to dummy images.")

            if not dataset_prepared:
                logger.info("[Hailo8L] Generating dummy calibration images...")
                await asyncio.to_thread(self._generate_dummy_calib, str(calib_dir), 8, (w, h))

            # 4. Lanzar Hailo Docker
            docker_cmd = [
                "docker", "run", "--rm",
                "-v", f"{shared_dir}:/shared_with_docker",
                HAILO_DOCKER_IMAGE,
                "bash", "-c",
                f"cd / && hailomz compile "
                f"--ckpt shared_with_docker/model.onnx "
                f"--calib-path shared_with_docker/calib "
                f"--yaml {yaml_path} "
                f"--classes {num_classes} "
                f"--hw-arch hailo8l "
                f"--output-dir shared_with_docker"
            ]
            redis = getattr(self, "redis_client", None)
            cancel_key = f"cancel:compile:{model_id}"
            if redis and await redis.exists(cancel_key):
                raise asyncio.CancelledError()

            try:
                proc = await asyncio.create_subprocess_exec(
                    *docker_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                
                cancellation_task = None
                if redis:
                    async def check_cancel():
                        try:
                            while True:
                                if await redis.exists(cancel_key):
                                    logger.info(f"Cancellation key {cancel_key} detected. Terminating Docker compiler...")
                                    try:
                                        proc.terminate()
                                        await asyncio.sleep(1)
                                        proc.kill()
                                    except ProcessLookupError:
                                        pass
                                    break
                                await asyncio.sleep(2)
                        except asyncio.CancelledError:
                            pass
                    cancellation_task = asyncio.create_task(check_cancel())

                try:
                    stdout, stderr = await proc.communicate()
                finally:
                    if cancellation_task:
                        cancellation_task.cancel()
                        try:
                            await cancellation_task
                        except asyncio.CancelledError:
                            pass

                if redis and await redis.exists(cancel_key):
                    raise asyncio.CancelledError()

                if proc.returncode != 0:
                    err = stderr.decode()[-2000:]
                    logger.error(f"[Hailo8L] Docker compilation failed:\n{err}")
                    return CompilationResult(success=False, error=f"hailomz compile failed: {err}")
            except FileNotFoundError:
                return CompilationResult(success=False, error="Docker not found on host")

            # 5. Buscar .hef generado
            hef_files = list(shared_dir.glob("*.hef"))
            if not hef_files:
                return CompilationResult(success=False, error="No .hef found after compilation")
            hef_path = hef_files[0]

            # 6. Subir .hef a MinIO
            hef_data = await asyncio.to_thread(hef_path.read_bytes)
            compiled_key = f"{model_id}/model.hef"
            sha = await upload_bytes("compiled", compiled_key, hef_data)

            logger.info(f"[Hailo8L] Compilation successful → {compiled_key}")
            return CompilationResult(
                success=True, compiled_key=compiled_key, compiled_sha256=sha)

    def _export_onnx(self, pt_path: str, onnx_path: str) -> None:
        from ultralytics import YOLO
        model = YOLO(pt_path)
        exported = model.export(format="onnx", batch=1, nms=False, opset=11)
        import shutil
        shutil.move(str(exported), onnx_path)

    def _prepare_calibration_images(
        self,
        dataset_dir: Path,
        calib_dir: Path,
        target_size: tuple[int, int],
        num_images: int = 1024
    ) -> int:
        from PIL import Image
        import random
        
        calib_dir.mkdir(parents=True, exist_ok=True)
        valid_extensions = {".jpg", ".jpeg", ".png"}
        
        all_images = []
        for root, _, files in os.walk(dataset_dir):
            for f in files:
                p = Path(root) / f
                if p.suffix.lower() in valid_extensions:
                    all_images.append(p)
                    
        if not all_images:
            raise ValueError("No images found in dataset")
            
        random.shuffle(all_images)
        selected = all_images[:num_images]
        
        valid_count = 0
        target_w, target_h = target_size
        
        for img_path in selected:
            try:
                # Verify image integrity before processing
                with Image.open(img_path) as img:
                    img.verify()
                with Image.open(img_path) as img:
                    img = img.convert("RGB")
                    
                    # Scale so shortest side covers target
                    ratio = max(target_w / img.width, target_h / img.height)
                    new_w = int(img.width * ratio)
                    new_h = int(img.height * ratio)
                    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    
                    # Centre crop
                    left = (img.width - target_w) // 2
                    top = (img.height - target_h) // 2
                    img = img.crop((left, top, left + target_w, top + target_h))
                    
                    out_path = calib_dir / f"calib_{valid_count}.jpg"
                    img.save(out_path, format="JPEG", quality=95)
                    valid_count += 1
            except Exception as e:
                logger.warning(f"Failed to process image {img_path} for calibration: {e}")
                continue
                
        return valid_count

    def _generate_dummy_calib(self, calib_dir: str, n: int, size: tuple[int, int]) -> None:
        try:
            from PIL import Image
            for i in range(n):
                img = Image.new("RGB", size, color=(0, 0, 0))
                img.save(os.path.join(calib_dir, f"calib_{i}.jpg"))
        except ImportError:
            # Fallback: escribir JPEG mínimo válido
            import struct
            for i in range(n):
                path = os.path.join(calib_dir, f"calib_{i}.jpg")
                open(path, "wb").write(b"\xff\xd8\xff\xd9")  # minimal JPEG
