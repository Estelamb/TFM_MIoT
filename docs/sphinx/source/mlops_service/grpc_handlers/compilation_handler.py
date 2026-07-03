"""
Compilation Service Handler
============================
Orchestrates the compilation of .pt models for each hardware target:

  hailo8 / hailo8l  → HailoCompiler  (launches Docker with Hailo AI SW Suite)
  rpi_ai_cam        → AICamCompiler  (MCT + imx500-converter in Python)
  rpi               → RPiCPUCompiler (ONNX export in Docker)
  jetson_orin_nano  → stub (TensorRT, pending)

The handler is non-blocking: CompileModel launches the compilation as an
asyncio task and returns status="compiling" immediately. The client can
poll status with GetCompilationStatus.
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
                classes_data = json.load(f)
            
            if isinstance(classes_data, list):
                return [str(x) for x in classes_data]
            elif isinstance(classes_data, dict):
                try:
                    # Format A: {"0": "alert", "1": "drowsy"} (index -> name)
                    first_key = next(iter(classes_data.keys()))
                    int(first_key)
                    sorted_keys = sorted(classes_data.keys(), key=lambda k: int(k))
                    return [str(classes_data[k]) for k in sorted_keys]
                except (ValueError, TypeError):
                    try:
                        # Format B: {"alert": 0, "drowsy": 1} (name -> index)
                        sorted_keys = sorted(classes_data.keys(), key=lambda k: int(classes_data[k]))
                        return [str(k) for k in sorted_keys]
                    except (ValueError, TypeError):
                        return sorted([str(k) for k in classes_data.keys()])
            else:
                raise ValueError("'classes.json' must be a JSON list or dictionary.")


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
        # Clear any cached job results/definitions in Redis to allow immediate retries
        await pool.delete(f"arq:job:compile:{req.model_id}")
        await pool.delete(f"arq:result:compile:{req.model_id}")

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
            _job_id=f"compile:{req.model_id}",   # idempotency key
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
        # Clear any cached job results/definitions in Redis to allow immediate retries
        await pool.delete(f"arq:job:train:{req.model_id}")
        await pool.delete(f"arq:result:train:{req.model_id}")

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
        from app.sensors import get_sensors_data, get_sensors
        sensors_data = get_sensors_data()
        return compilation_pb2.GetSupportedSensorsResponse(
            sensors=get_sensors(),   # only subdriver keys (with "/")
            labels=sensors_data      # full map including category keys for labels
        )

    async def GetSupportedActuators(self, req, ctx):
        from app.actuators import get_actuators_data, get_actuators
        actuators_data = get_actuators_data()
        return compilation_pb2.GetSupportedActuatorsResponse(
            actuators=get_actuators(),   # only subdriver keys (with "/")
            labels=actuators_data        # full map including category keys for labels
        )

    async def GetSupportedOthers(self, req, ctx):
        from app.others import get_others_data, get_others
        others_data = get_others_data()
        return compilation_pb2.GetSupportedOthersResponse(
            others=get_others(),   # only subdriver keys (with "/")
            labels=others_data     # full map including category keys for labels
        )



    async def _notify(self, model_id: str, status: str, compiled_key: str,
                      compiled_sha256: str, hardware_type: str, error: str):
        await self._ai_stub.UpdateModelCompiled(ai_pb2.UpdateModelCompiledRequest(
            id=model_id, compiled_key=compiled_key, compiled_sha256=compiled_sha256,
            hardware_type=hardware_type, compile_status=status, compile_error=error,
        ))
