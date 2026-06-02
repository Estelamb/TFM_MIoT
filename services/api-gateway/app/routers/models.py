import hashlib, io, uuid
from fastapi import APIRouter, Depends, File, Form, UploadFile
from app.auth.jwt import verify_token
from app.stubs import get_stub
from shared.proto_gen import ai_pb2, compilation_pb2
from shared.utils.minio import upload_bytes

router = APIRouter(prefix="/api/models", tags=["models"])

@router.post("", status_code=201)
async def upload_model(
    name: str = Form(...), description: str = Form(""),
    hardware_type: str = Form(...), compile: bool = Form(True),
    file: UploadFile = File(...), _=Depends(verify_token),
):
    data = await file.read()
    model_id = str(uuid.uuid4())
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "pt"
    source_key = f"{model_id}/source.{ext}"
    sha = await upload_bytes("models", source_key, data)

    ai_stub = get_stub("ai")
    m = await ai_stub.UploadModel(ai_pb2.UploadModelRequest(
        name=name, description=description, source_key=source_key, source_sha256=sha))

    if compile:
        comp_stub = get_stub("compilation")
        await comp_stub.CompileModel(compilation_pb2.CompileModelRequest(
            model_id=m.id, source_key=source_key, hardware_type=hardware_type))

    return {"id": m.id, "name": m.name, "compile_status": m.compile_status, "created_at": m.created_at}

@router.get("")
async def list_models(_=Depends(verify_token)):
    r = await get_stub("ai").ListModels(ai_pb2.ListModelsRequest())
    return [{"id": m.id, "name": m.name, "hardware_type": m.hardware_type,
             "compile_status": m.compile_status, "created_at": m.created_at}
            for m in r.models]

@router.get("/{model_id}")
async def get_model(model_id: str, _=Depends(verify_token)):
    m = await get_stub("ai").GetModel(ai_pb2.GetModelRequest(id=model_id))
    return {"id": m.id, "name": m.name, "description": m.description,
            "hardware_type": m.hardware_type, "compile_status": m.compile_status,
            "compile_error": m.compile_error, "created_at": m.created_at}

@router.delete("/{model_id}", status_code=204)
async def delete_model(model_id: str, _=Depends(verify_token)):
    await get_stub("ai").DeleteModel(ai_pb2.DeleteModelRequest(id=model_id))
