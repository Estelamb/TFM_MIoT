import uuid
from fastapi import APIRouter, Depends, File, Form, UploadFile
from app.auth.jwt import verify_token
from app.stubs import get_stub
from shared.proto_gen import script_pb2
from shared.utils.minio import upload_bytes

router = APIRouter(prefix="/api/scripts", tags=["scripts"])

@router.post("", status_code=201)
async def upload_script(
    name: str = Form(...), description: str = Form(""),
    hardware_type: str = Form(...),
    file: UploadFile = File(...), _=Depends(verify_token),
):
    data = await file.read()
    script_id = str(uuid.uuid4())
    script_key = f"{script_id}/script.py"
    sha = await upload_bytes("scripts", script_key, data)
    sc = await get_stub("script").UploadScript(script_pb2.UploadScriptRequest(
        name=name, description=description, hardware_type=hardware_type,
        script_key=script_key, script_sha256=sha))
    return {"id": sc.id, "name": sc.name, "hardware_type": sc.hardware_type, "created_at": sc.created_at}

@router.get("")
async def list_scripts(_=Depends(verify_token)):
    r = await get_stub("script").ListScripts(script_pb2.ListScriptsRequest())
    from shared.utils.minio import get_minio
    from app.config import get_settings
    s_settings = get_settings()
    minio = get_minio()
    
    scripts_list = []
    for s in r.scripts:
        content = ""
        if s.script_key:
            try:
                resp = await minio.get_object(s_settings.minio_bucket_scripts, s.script_key)
                content_bytes = await resp.read()
                content = content_bytes.decode("utf-8")
            except Exception:
                pass
        scripts_list.append({
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "hardware_type": s.hardware_type,
            "script_sha256": s.script_sha256,
            "created_at": s.created_at,
            "content": content
        })
    return scripts_list

@router.get("/{script_id}")
async def get_script(script_id: str, _=Depends(verify_token)):
    s = await get_stub("script").GetScript(script_pb2.GetScriptRequest(id=script_id))
    from shared.utils.minio import get_minio
    from app.config import get_settings
    s_settings = get_settings()
    minio = get_minio()
    
    content = ""
    if s.script_key:
        try:
            resp = await minio.get_object(s_settings.minio_bucket_scripts, s.script_key)
            content_bytes = await resp.read()
            content = content_bytes.decode("utf-8")
        except Exception:
            pass
            
    return {
        "id": s.id,
        "name": s.name,
        "description": s.description,
        "hardware_type": s.hardware_type,
        "script_sha256": s.script_sha256,
        "created_at": s.created_at,
        "content": content
    }

@router.delete("/{script_id}", status_code=204)
async def delete_script(script_id: str, _=Depends(verify_token)):
    await get_stub("script").DeleteScript(script_pb2.DeleteScriptRequest(id=script_id))
