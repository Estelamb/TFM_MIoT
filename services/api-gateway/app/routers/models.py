import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
import redis.asyncio as aioredis
from app.auth.jwt import verify_token
from app.stubs import get_stub
from shared.proto_gen import ai_pb2, compilation_pb2
from shared.utils.minio import upload_bytes, presigned_url

router = APIRouter(prefix="/api/models", tags=["models"])

ALLOWED_BASE_MODELS = {
    "yolov10b.pt", "yolov10n.pt", "yolov10s.pt", "yolov10x.pt",
    "yolov11l.pt", "yolov11m.pt", "yolov11n.pt", "yolov11s.pt", "yolov11x.pt",
    "yolov3_416.pt", "yolov3_gluon_416.pt", "yolov3_gluon.pt", "yolov3.pt",
    "yolov4_leaky.pt", "yolov5m_6.1.pt", "yolov5m6_6.1.pt",
    "yolov5m_vehicles_nv12.pt", "yolov5m_vehicles.pt", "yolov5m_vehicles_yuy2.pt",
    "yolov5m_wo_spp.pt", "yolov5m_wo_spp_yuy2.pt", "yolov5m.pt",
    "yolov5s_bbox_decoding_only.pt", "yolov5s_c3tr.pt", "yolov5s_personface_nv12.pt",
    "yolov5s_personface_rgbx.pt", "yolov5s_personface.pt", "yolov5s_wo_spp.pt",
    "yolov5s.pt", "yolov5xs_wo_spp_nms_core.pt", "yolov5xs_wo_spp.pt",
    "yolov6n_0.2.1_nms_core.pt", "yolov6n_0.2.1.pt", "yolov6n.pt",
    "yolov7e6.pt", "yolov7_tiny.pt", "yolov7.pt", "yolov8l.pt",
    "yolov8m.pt", "yolov8n.pt", "yolov8s_bbox_decoding_only.pt",
    "yolov8s.pt", "yolov8x.pt", "yolov9c.pt",
    "yolox_l_leaky.pt", "yolox_s_leaky.pt", "yolox_s_wide_leaky.pt",
    "yolox_tiny.pt"
}


@router.get("/base-model-options")
async def get_base_model_options(_=Depends(verify_token)):
    from shared.utils.minio import get_minio
    from app.config import get_settings
    s = get_settings()
    minio = get_minio()
    try:
        objects = await minio.list_objects(s.minio_bucket_base_models)
        return sorted([obj.object_name for obj in objects])
    except Exception:
        return sorted(list(ALLOWED_BASE_MODELS))


@router.get("/base-models/{filename}/download")
async def download_base_model(filename: str, _=Depends(verify_token)):
    from shared.utils.minio import get_minio, presigned_url
    from app.config import get_settings
    s = get_settings()
    minio = get_minio()
    try:
        try:
            objects = await minio.list_objects(s.minio_bucket_base_models)
            allowed = {obj.object_name for obj in objects}
        except Exception:
            allowed = ALLOWED_BASE_MODELS

        if filename not in allowed:
            raise HTTPException(404, f"Base model file '{filename}' not found")

        url = await presigned_url("base-models", filename)
        return {"url": url}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error generating download URL: {e}")


@router.post("", status_code=201)
async def upload_model(
    name: str = Form(...), description: str = Form(""),
    hardware_type: str = Form(""), compile: bool = Form(False),
    dataset_id: str = Form(""),
    base_architecture: str = Form(...),
    epochs: int = Form(None),
    input_size: str = Form(None),
    batch_size: int = Form(None),
    file: UploadFile = File(...), _=Depends(verify_token),
):
    if not base_architecture or not base_architecture.strip():
        raise HTTPException(400, "base_architecture is required")

    base_architecture = base_architecture.strip()
    if not base_architecture.endswith(".pt"):
        base_architecture += ".pt"

    from shared.utils.minio import get_minio
    from app.config import get_settings
    s = get_settings()
    minio = get_minio()
    try:
        objects = await minio.list_objects(s.minio_bucket_base_models)
        allowed = {obj.object_name for obj in objects}
    except Exception:
        allowed = ALLOWED_BASE_MODELS

    if base_architecture not in allowed:
        raise HTTPException(400, f"base_architecture '{base_architecture}' is not in the allowed list")

    if epochs is not None and epochs <= 0:
        raise HTTPException(400, "epochs must be a positive integer")

    if input_size:
        input_size = input_size.strip().lower()
        import re
        if not re.match(r"^\d+x\d+$", input_size):
            raise HTTPException(400, "input_size must be in format WxH, e.g. 640x640")

    if batch_size is not None and batch_size <= 0:
        raise HTTPException(400, "batch_size must be a positive integer")

    data = await file.read()
    model_id = str(uuid.uuid4())
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "pt"
    source_key = f"{model_id}/source.{ext}"
    sha = await upload_bytes("models", source_key, data)

    ai_stub = get_stub("ai")
    m = await ai_stub.UploadModel(ai_pb2.UploadModelRequest(
        name=name,
        description=description,
        source_key=source_key,
        source_sha256=sha,
        dataset_id=dataset_id or "",
        base_architecture=base_architecture or "",
        epochs=epochs or 0,
        input_size=input_size or "",
        batch_size=batch_size or 0,
    ))

    if compile and hardware_type:
        if not m.dataset_id:
            raise HTTPException(400, "dataset_id is required when compile=true")
        d = await ai_stub.GetDataset(ai_pb2.GetDatasetRequest(id=m.dataset_id))
        comp_stub = get_stub("compilation")
        await comp_stub.CompileModel(compilation_pb2.CompileModelRequest(
            model_id=m.id,
            source_key=source_key,
            hardware_type=hardware_type,
            dataset_id=d.id,
            dataset_key=d.object_key,
            base_architecture=m.base_architecture,
            input_size=m.input_size,
        ))
    else:
        m = await ai_stub.UpdateModelCompiled(ai_pb2.UpdateModelCompiledRequest(
            id=m.id,
            compiled_key="",
            compiled_sha256="",
            hardware_type="",
            compile_status="ready",
            compile_error="",
            source_key=source_key,
            source_sha256=sha
        ))

    return _model_resp(m)


@router.get("")
async def list_models(_=Depends(verify_token)):
    r = await get_stub("ai").ListModels(ai_pb2.ListModelsRequest())
    return [_model_resp(m) for m in r.models]


@router.get("/{model_id}")
async def get_model(model_id: str, _=Depends(verify_token)):
    m = await get_stub("ai").GetModel(ai_pb2.GetModelRequest(id=model_id))
    return _model_resp(m)


@router.post("/{model_id}/dataset/{dataset_id}")
async def associate_model_dataset(model_id: str, dataset_id: str, _=Depends(verify_token)):
    import re
    uuid_re = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)
    if not uuid_re.match(dataset_id):
        raise HTTPException(400, "Invalid dataset ID format")
    if not uuid_re.match(model_id):
        raise HTTPException(400, "Invalid model ID format")
    try:
        m = await get_stub("ai").AssociateModelDataset(
            ai_pb2.AssociateModelDatasetRequest(
                model_id=model_id,
                dataset_id=dataset_id,
            )
        )
    except Exception as e:
        err_str = str(e)
        if "NOT_FOUND" in err_str or "not found" in err_str.lower():
            raise HTTPException(404, "Model or dataset not found")
        raise HTTPException(400, "Failed to associate dataset. Please ensure the dataset exists.")
    return {
        "id": m.id,
        "dataset_id": m.dataset_id,
        "compile_status": m.compile_status,
    }


@router.delete("/{model_id}", status_code=204)
async def delete_model(model_id: str, _=Depends(verify_token)):
    from app.config import get_settings
    s_settings = get_settings()
    try:
        redis_client = aioredis.from_url(s_settings.redis_url)
        await redis_client.set(f"cancel:train:{model_id}", "1", ex=300)
        await redis_client.set(f"cancel:compile:{model_id}", "1", ex=300)
        await redis_client.close()
    except Exception:
        pass
    await get_stub("ai").DeleteModel(ai_pb2.DeleteModelRequest(id=model_id))


@router.get("/{model_id}/download/source")
async def download_model_source(model_id: str, _=Depends(verify_token)):
    m = await get_stub("ai").GetModel(ai_pb2.GetModelRequest(id=model_id))
    if not m.source_key:
        raise HTTPException(404, "Source model file not found")
    try:
        from shared.utils.minio import get_minio
        from app.config import get_settings
        s_cfg = get_settings()
        minio = get_minio()
        await minio.stat_object(s_cfg.minio_bucket_models, m.source_key)
    except Exception:
        raise HTTPException(404, "Model file not found in storage. It may not have been uploaded correctly.")
    url = await presigned_url("models", m.source_key)
    return {"url": url}


@router.get("/{model_id}/download/compiled")
async def download_model_compiled(model_id: str, _=Depends(verify_token)):
    m = await get_stub("ai").GetModel(ai_pb2.GetModelRequest(id=model_id))
    if not m.compiled_key:
        raise HTTPException(404, "Compiled model file not found")
    url = await presigned_url("compiled", m.compiled_key)
    return {"url": url}


import asyncio
from fastapi.responses import StreamingResponse

@router.get("/{model_id}/logs")
async def stream_model_logs(model_id: str, _=Depends(verify_token)):
    from app.config import get_settings
    import redis.asyncio as aioredis
    
    async def log_generator():
        s = get_settings()
        redis_client = aioredis.from_url(s.redis_url)
        try:
            redis_list = f"train_logs:{model_id}_list"
            redis_channel = f"train_logs:{model_id}"
            
            # Send existing logs first
            existing_logs = await redis_client.lrange(redis_list, 0, -1)
            for log in existing_logs:
                # SSE format
                yield f"data: {log.decode('utf-8')}\n\n"
            
            # Subscribe to new logs
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(redis_channel)
            
            while True:
                try:
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message:
                        yield f"data: {message['data'].decode('utf-8')}\n\n"
                    # Small sleep to yield control
                    await asyncio.sleep(0.01)
                except asyncio.CancelledError:
                    break
        except Exception as e:
            yield f"data: ERROR: {str(e)}\n\n"
        finally:
            if 'pubsub' in locals():
                await pubsub.unsubscribe(redis_channel)
                await pubsub.close()
            await redis_client.close()

    return StreamingResponse(log_generator(), media_type="text/event-stream")


from pydantic import BaseModel


class TrainModelRequestSchema(BaseModel):
    name: str
    description: str = ""
    dataset_id: str
    base_model: str
    epochs: int = 20
    input_size: str = "640x640"
    gpu_percent: float = 0.9
    device: str = "0"


@router.post("/train", status_code=201)
async def train_model(req: TrainModelRequestSchema, _=Depends(verify_token)):
    if not req.base_model or not req.base_model.strip():
        raise HTTPException(400, "base_model is required")
    ai_stub = get_stub("ai")
    comp_stub = get_stub("compilation")

    # 1. Fetch the dataset from AI Service to get the object_key
    try:
        d = await ai_stub.GetDataset(ai_pb2.GetDatasetRequest(id=req.dataset_id))
    except Exception as e:
        raise HTTPException(404, f"Dataset not found: {e}")

    if not d.object_key:
        raise HTTPException(400, "Dataset has no file uploaded. Please upload a ZIP file to the dataset first.")

    # 2. Register the model record in AI Service
    try:
        m = await ai_stub.UploadModel(ai_pb2.UploadModelRequest(
            name=req.name,
            description=req.description,
            source_key=f"training/{req.name}_placeholder",
            source_sha256="",
            dataset_id=req.dataset_id,
            base_architecture=req.base_model,
            epochs=req.epochs,
            input_size=req.input_size,
            batch_size=0,
        ))
    except Exception as e:
        raise HTTPException(500, f"Failed to register training model: {e}")

    # 3. Call Compilation Service to start background training
    try:
        await comp_stub.TrainModel(compilation_pb2.TrainModelRequest(
            model_id=m.id,
            name=req.name,
            dataset_id=req.dataset_id,
            dataset_key=d.object_key,
            base_architecture=req.base_model,
            epochs=req.epochs,
            input_size=req.input_size,
            gpu_percent=req.gpu_percent,
            device=req.device
        ))
    except Exception as e:
        await ai_stub.UpdateModelCompiled(ai_pb2.UpdateModelCompiledRequest(
            id=m.id,
            compiled_key="",
            compiled_sha256="",
            hardware_type="",
            compile_status="failed",
            compile_error=f"Failed to start training: {e}",
            source_key=m.source_key,
            source_sha256=""
        ))
        raise HTTPException(500, f"Failed to start training task: {e}")

    return {**_model_resp(m), "compile_status": "training"}


class UpdateModelRequestSchema(BaseModel):
    name: str
    description: str = ""
    epochs: int = None
    input_size: str = None
    batch_size: int = None
    base_architecture: str = None


@router.put("/{model_id}")
async def update_model(model_id: str, req: UpdateModelRequestSchema, _=Depends(verify_token)):
    if req.epochs is not None and req.epochs <= 0:
        raise HTTPException(400, "epochs must be a positive integer")

    if req.input_size:
        req.input_size = req.input_size.strip().lower()
        import re
        if not re.match(r"^\d+x\d+$", req.input_size):
            raise HTTPException(400, "input_size must be in format WxH, e.g. 640x640")

    if req.batch_size is not None and req.batch_size <= 0:
        raise HTTPException(400, "batch_size must be a positive integer")

    base_arch_formatted = ""
    if req.base_architecture and req.base_architecture.strip():
        base_arch_formatted = req.base_architecture.strip()
        if not base_arch_formatted.endswith(".pt"):
            base_arch_formatted += ".pt"

        from shared.utils.minio import get_minio
        from app.config import get_settings
        s = get_settings()
        minio = get_minio()
        try:
            objects = await minio.list_objects(s.minio_bucket_base_models)
            allowed = {obj.object_name for obj in objects}
        except Exception:
            allowed = ALLOWED_BASE_MODELS

        if base_arch_formatted not in allowed:
            raise HTTPException(400, f"base_architecture '{base_arch_formatted}' is not in the allowed list")

    try:
        m = await get_stub("ai").UpdateModel(ai_pb2.UpdateModelRequest(
            id=model_id,
            name=req.name,
            description=req.description,
            epochs=req.epochs or 0,
            input_size=req.input_size or "",
            batch_size=req.batch_size or 0,
            base_architecture=base_arch_formatted,
        ))
        return _model_resp(m)
    except Exception as e:
        raise HTTPException(404, f"Model not found: {e}")


def _model_resp(m) -> dict:
    return {
        "id": m.id,
        "name": m.name,
        "description": m.description,
        "hardware_type": m.hardware_type,
        "dataset_id": m.dataset_id or None,
        "compile_status": m.compile_status,
        "compile_error": m.compile_error or None,
        "created_at": m.created_at,
        "base_architecture": m.base_architecture,
        "epochs": m.epochs or None,
        "input_size": m.input_size or None,
        "batch_size": m.batch_size or None,
    }
