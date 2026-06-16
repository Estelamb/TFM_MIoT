"""
Compilation Service Handler
============================
Orquesta la compilación de modelos .pt para cada hardware:

  hailo8 / hailo8l  → HailoCompiler  (lanza Docker con Hailo AI SW Suite)
  rpi_ai_cam        → AICamCompiler  (MCT + imx500-converter en Python)
  rpi               → stub (TFLite, pendiente)
  jetson_orin_nano  → stub (TensorRT, pendiente)

El handler es no-bloqueante: CompileModel lanza la compilación como tarea
asyncio y devuelve status="compiling" inmediatamente. El cliente puede
hacer polling con GetCompilationStatus.
"""
import asyncio
import logging
import os
import tempfile
import zipfile
import json

import grpc
from arq import create_pool
from arq.connections import RedisSettings
from shared.proto_gen import compilation_pb2, compilation_pb2_grpc, ai_pb2, ai_pb2_grpc
from app.compilers import discover_compilers
from app.compilers.base import CompilerBase, CompilationResult
from shared.utils.minio import get_minio

logger = logging.getLogger(__name__)

async def extract_classes_from_dataset(bucket: str, dataset_key: str) -> list[str]:
    """Downloads the dataset zip and extracts class names ordered by index from classes.json."""
    if not dataset_key:
        return []
    minio = get_minio()
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "dataset.zip")
        await minio.fget_object(bucket, dataset_key, zip_path)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            classes_file = None
            for name in zip_ref.namelist():
                if name.endswith("classes.json"):
                    classes_file = name
                    break
            if not classes_file:
                raise ValueError("classes.json not found in dataset zip")
            with zip_ref.open(classes_file) as f:
                classes_dict = json.load(f)
            # Sort class names by their index value
            sorted_classes = sorted(classes_dict.keys(), key=lambda k: classes_dict[k])
            return sorted_classes


def _build_registry(minio_bucket_models: str, minio_bucket_compiled: str) -> dict:
    return discover_compilers(minio_bucket_models, minio_bucket_compiled)


class CompilationServiceHandler(compilation_pb2_grpc.CompilationServiceServicer):
    def __init__(self, ai_service_grpc: str, minio_bucket_models: str,
                 minio_bucket_compiled: str, redis_url: str):
        self._ai_channel = grpc.aio.insecure_channel(ai_service_grpc)
        self._ai_stub = ai_pb2_grpc.AIServiceStub(self._ai_channel)
        self._registry = _build_registry(minio_bucket_models, minio_bucket_compiled)
        self._redis_settings = RedisSettings.from_dsn(redis_url)
        self._redis_pool = None  # initialised lazily on first use

    async def _get_pool(self):
        if self._redis_pool is None:
            self._redis_pool = await create_pool(self._redis_settings, default_queue_name="mlops_queue")
        return self._redis_pool

    async def CompileModel(self, req, ctx):
        logger.info(f"CompileModel: model_id={req.model_id} hw={req.hardware_type}")
        dataset_key = (req.dataset_key or "").strip()

        compiler = self._registry.get(req.hardware_type)
        if compiler is None:
            await self._notify(req.model_id, "failed", "", "", req.hardware_type,
                               f"No compiler for hardware: {req.hardware_type}")
            return compilation_pb2.CompileModelResponse(
                model_id=req.model_id, status="failed",
                error=f"No compiler implemented for: {req.hardware_type}")

        await self._notify(req.model_id, "compiling", "", "", req.hardware_type, "")

        pool = await self._get_pool()
        await pool.enqueue_job(
            "compile_job",
            model_id=req.model_id,
            source_key=req.source_key,
            hardware_type=req.hardware_type,
            num_classes=req.num_classes,
            class_names=list(req.class_names),
            dataset_id=req.dataset_id or "",
            dataset_key=dataset_key,
            base_architecture=req.base_architecture or "",
            input_size=req.input_size or "",
            _job_id=f"compile:{req.model_id}",   # idempotency key — prevents duplicate jobs
        )
        logger.info(f"compile_job enqueued for model {req.model_id}")

        return compilation_pb2.CompileModelResponse(
            model_id=req.model_id, status="compiling")

    async def TrainModel(self, req, ctx):
        logger.info(f"TrainModel: model_id={req.model_id}")
        dataset_key = (req.dataset_key or "").strip()

        if not dataset_key:
            msg = "Dataset key is required for training"
            await self._notify(req.model_id, "failed", "", "", "", msg)
            return compilation_pb2.TrainModelResponse(model_id=req.model_id, status="failed")

        await self._notify(req.model_id, "training", "", "", "", "")

        pool = await self._get_pool()
        await pool.enqueue_job(
            "train_job",
            model_id=req.model_id,
            name=req.name,
            dataset_id=req.dataset_id,
            dataset_key=dataset_key,
            base_architecture=req.base_architecture or "yolov8n.pt",
            epochs=req.epochs or 20,
            input_size=req.input_size or "640x640",
            gpu_percent=req.gpu_percent or 0.9,
            device=req.device or "0",
            _job_id=f"train:{req.model_id}",   # idempotency key
        )
        logger.info(f"train_job enqueued for model {req.model_id}")

        return compilation_pb2.TrainModelResponse(model_id=req.model_id, status="training")

    async def GetCompilationStatus(self, req, ctx):
        model = await self._ai_stub.GetModel(ai_pb2.GetModelRequest(id=req.model_id))
        return compilation_pb2.CompileModelResponse(
            model_id=model.id,
            status=model.compile_status,
            compiled_key=model.compiled_key,
            compiled_sha256=model.compiled_sha256,
            error=model.compile_error,
        )

    async def GetSupportedHardware(self, req, ctx):
        from app.compilers import get_architectures_data
        archs_data = get_architectures_data()
        return compilation_pb2.GetSupportedHardwareResponse(
            hardware_types=sorted(list(archs_data.keys())),
            labels=archs_data
        )

    async def GetSupportedSensors(self, req, ctx):
        from app.sensors import get_sensors_data
        sensors_data = get_sensors_data()
        return compilation_pb2.GetSupportedSensorsResponse(
            sensors=sorted(list(sensors_data.keys())),
            labels=sensors_data
        )

    async def GetSupportedActuators(self, req, ctx):
        from app.actuators import get_actuators_data
        actuators_data = get_actuators_data()
        return compilation_pb2.GetSupportedActuatorsResponse(
            actuators=sorted(list(actuators_data.keys())),
            labels=actuators_data
        )


    async def _notify(self, model_id: str, status: str, compiled_key: str,
                      compiled_sha256: str, hardware_type: str, error: str):
        await self._ai_stub.UpdateModelCompiled(ai_pb2.UpdateModelCompiledRequest(
            id=model_id, compiled_key=compiled_key, compiled_sha256=compiled_sha256,
            hardware_type=hardware_type, compile_status=status, compile_error=error,
        ))
