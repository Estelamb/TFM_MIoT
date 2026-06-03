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

import grpc
from shared.proto_gen import compilation_pb2, compilation_pb2_grpc, ai_pb2, ai_pb2_grpc
from app.compilers.hailo import HailoCompiler
from app.compilers.aicam import AICamCompiler
from app.compilers.base import CompilerBase, CompilationResult

logger = logging.getLogger(__name__)


def _build_registry(minio_bucket_models: str, minio_bucket_compiled: str) -> dict:
    hailo = HailoCompiler(minio_bucket_models, minio_bucket_compiled)
    aicam = AICamCompiler(minio_bucket_models, minio_bucket_compiled)
    return {
        "hailo8":          hailo,
        "hailo8l":         hailo,
        "rpi_ai_cam":      aicam,
        # "rpi":           TFLiteCompiler(),       # pendiente
        # "jetson_orin_nano": TensorRTCompiler(),  # pendiente
    }


class CompilationServiceHandler(compilation_pb2_grpc.CompilationServiceServicer):
    def __init__(self, ai_service_grpc: str, minio_bucket_models: str, minio_bucket_compiled: str):
        self._ai_channel = grpc.aio.insecure_channel(ai_service_grpc)
        self._ai_stub = ai_pb2_grpc.AIServiceStub(self._ai_channel)
        self._registry = _build_registry(minio_bucket_models, minio_bucket_compiled)

    async def CompileModel(self, req, ctx):
        logger.info(f"CompileModel: model_id={req.model_id} hw={req.hardware_type}")
        dataset_key = (req.dataset_key or "").strip()

        if not dataset_key:
            msg = "Dataset version is required for compilation"
            await self._notify(req.model_id, "failed", "", "", req.hardware_type, msg)
            return compilation_pb2.CompileModelResponse(
                model_id=req.model_id,
                status="failed",
                error=msg,
            )

        compiler: CompilerBase | None = self._registry.get(req.hardware_type)
        if compiler is None:
            await self._notify(req.model_id, "failed", "", "", req.hardware_type,
                               f"No compiler for hardware: {req.hardware_type}")
            return compilation_pb2.CompileModelResponse(
                model_id=req.model_id, status="failed",
                error=f"No compiler implemented for: {req.hardware_type}")

        # Marcar como compiling en ai-service
        await self._notify(req.model_id, "compiling", "", "", req.hardware_type, "")

        # Lanzar compilación en background (no bloqueante)
        asyncio.create_task(
            self._run_compilation(compiler, req.model_id, req.source_key,
                                  req.hardware_type, req.num_classes, list(req.class_names),
                                  req.dataset_version_id or "", dataset_key)
        )

        return compilation_pb2.CompileModelResponse(
            model_id=req.model_id, status="compiling")

    async def GetCompilationStatus(self, req, ctx):
        model = await self._ai_stub.GetModel(ai_pb2.GetModelRequest(id=req.model_id))
        return compilation_pb2.CompileModelResponse(
            model_id=model.id,
            status=model.compile_status,
            compiled_key=model.compiled_key,
            compiled_sha256=model.compiled_sha256,
            error=model.compile_error,
        )

    async def _run_compilation(self, compiler: CompilerBase, model_id: str,
                                source_key: str, hardware_type: str,
                                num_classes: int, class_names: list[str],
                                dataset_version_id: str, dataset_key: str):
        try:
            result: CompilationResult = await compiler.compile(
                model_id=model_id, source_key=source_key,
                num_classes=num_classes, class_names=class_names,
                hardware_type=hardware_type,
                dataset_version_id=dataset_version_id,
                dataset_key=dataset_key,
            )
            if result.success:
                await self._notify(model_id, "ready", result.compiled_key,
                                   result.compiled_sha256, hardware_type, "")
                logger.info(f"Compilation OK: {model_id}")
            else:
                await self._notify(model_id, "failed", "", "", hardware_type, result.error)
                logger.error(f"Compilation failed: {model_id} — {result.error}")
        except Exception as e:
            await self._notify(model_id, "failed", "", "", hardware_type, str(e))
            logger.exception(f"Unexpected compilation error for {model_id}")

    async def _notify(self, model_id: str, status: str, compiled_key: str,
                      compiled_sha256: str, hardware_type: str, error: str):
        await self._ai_stub.UpdateModelCompiled(ai_pb2.UpdateModelCompiledRequest(
            id=model_id, compiled_key=compiled_key, compiled_sha256=compiled_sha256,
            hardware_type=hardware_type, compile_status=status, compile_error=error,
        ))
