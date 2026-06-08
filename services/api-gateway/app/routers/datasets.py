import io
import json
import uuid
import zipfile
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.auth.jwt import verify_token
from app.stubs import get_stub
from shared.proto_gen import ai_pb2
from shared.utils.minio import upload_bytes, presigned_url

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


def validate_dataset_zip(file_bytes: bytes) -> tuple[bool, str, int]:
    """Validate that the ZIP contains images/, labels/ and classes.json (can be inside a subfolder)."""
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            namelist = z.namelist()
            classes_paths = [p for p in namelist if p.endswith("classes.json")]
            if not classes_paths:
                return False, "Missing 'classes.json' in the zip file.", 0

            classes_path = classes_paths[0]
            base_dir = classes_path[:-len("classes.json")]

            images_prefix = f"{base_dir}images/"
            labels_prefix = f"{base_dir}labels/"

            has_images = any(p.startswith(images_prefix) and p != images_prefix for p in namelist)
            has_labels = any(p.startswith(labels_prefix) and p != labels_prefix for p in namelist)

            if not has_images:
                return False, f"Missing 'images/' directory or it is empty under '{base_dir}'.", 0
            if not has_labels:
                return False, f"Missing 'labels/' directory or it is empty under '{base_dir}'.", 0

            try:
                classes_content = z.read(classes_path)
                classes_data = json.loads(classes_content)
                if not isinstance(classes_data, dict):
                    return False, "'classes.json' must be a JSON object mapping indices to class names.", 0
                num_classes = len(classes_data)
            except Exception as je:
                return False, f"Failed to parse 'classes.json': {je}", 0

            return True, "", num_classes
    except zipfile.BadZipFile:
        return False, "The uploaded file is not a valid zip file.", 0
    except Exception as e:
        return False, f"Error validating zip file: {e}", 0


@router.post("", status_code=201)
async def create_dataset(
    name: str = Form(...),
    description: str = Form(""),
    file: UploadFile = File(None),
    _=Depends(verify_token),
):
    """Create a new dataset, optionally uploading a ZIP file immediately."""
    file_bytes = None
    num_classes = 0
    if file:
        file_bytes = await file.read()
        is_valid, err_msg, num_classes = validate_dataset_zip(file_bytes)
        if not is_valid:
            raise HTTPException(status_code=400, detail=err_msg)

    ai_stub = get_stub("ai")
    d = await ai_stub.UploadDataset(
        ai_pb2.UploadDatasetRequest(name=name, description=description)
    )

    if file and file_bytes:
        object_key = f"{d.id}/{uuid.uuid4()}-{file.filename or 'dataset.zip'}"
        sha = await upload_bytes("datasets", object_key, file_bytes)
        d = await ai_stub.SetDatasetFile(
            ai_pb2.SetDatasetFileRequest(
                dataset_id=d.id,
                object_key=object_key,
                sha256=sha,
                size_bytes=len(file_bytes),
                metadata=json.dumps({"num_classes": num_classes}),
            )
        )

    return _dataset_resp(d)


@router.get("")
async def list_datasets(_=Depends(verify_token)):
    r = await get_stub("ai").ListDatasets(ai_pb2.ListDatasetsRequest())
    return [_dataset_resp(d) for d in r.datasets]


@router.get("/{dataset_id}")
async def get_dataset(dataset_id: str, _=Depends(verify_token)):
    d = await get_stub("ai").GetDataset(ai_pb2.GetDatasetRequest(id=dataset_id))
    return _dataset_resp(d)


@router.delete("/{dataset_id}", status_code=204)
async def delete_dataset(dataset_id: str, _=Depends(verify_token)):
    await get_stub("ai").DeleteDataset(ai_pb2.DeleteDatasetRequest(id=dataset_id))


@router.put("/{dataset_id}/file", status_code=200)
async def replace_dataset_file(
    dataset_id: str,
    file: UploadFile = File(...),
    _=Depends(verify_token),
):
    """Replace the ZIP file of an existing dataset."""
    data = await file.read()
    is_valid, err_msg, num_classes = validate_dataset_zip(data)
    if not is_valid:
        raise HTTPException(status_code=400, detail=err_msg)

    object_key = f"{dataset_id}/{uuid.uuid4()}-{file.filename or 'dataset.zip'}"
    sha = await upload_bytes("datasets", object_key, data)

    d = await get_stub("ai").SetDatasetFile(
        ai_pb2.SetDatasetFileRequest(
            dataset_id=dataset_id,
            object_key=object_key,
            sha256=sha,
            size_bytes=len(data),
            metadata=json.dumps({"num_classes": num_classes}),
        )
    )
    return _dataset_resp(d)


@router.get("/{dataset_id}/download")
async def download_dataset(dataset_id: str, _=Depends(verify_token)):
    """Get a presigned download URL for the dataset ZIP."""
    d = await get_stub("ai").GetDataset(ai_pb2.GetDatasetRequest(id=dataset_id))
    if not d.object_key:
        raise HTTPException(404, "This dataset has no file uploaded yet.")
    try:
        from shared.utils.minio import get_minio
        from app.config import get_settings
        s_cfg = get_settings()
        minio = get_minio()
        await minio.stat_object(s_cfg.minio_bucket_datasets, d.object_key)
    except Exception:
        raise HTTPException(404, "Dataset file not found in storage.")
    url = await presigned_url("datasets", d.object_key)
    return {"url": url}


from pydantic import BaseModel


class UpdateDatasetRequestSchema(BaseModel):
    name: str
    description: str = ""


@router.put("/{dataset_id}")
async def update_dataset(dataset_id: str, req: UpdateDatasetRequestSchema, _=Depends(verify_token)):
    try:
        d = await get_stub("ai").UpdateDataset(ai_pb2.UpdateDatasetRequest(
            id=dataset_id,
            name=req.name,
            description=req.description,
        ))
        return _dataset_resp(d)
    except Exception as e:
        raise HTTPException(404, f"Dataset not found: {e}")


def _dataset_resp(d) -> dict:
    return {
        "id": d.id,
        "name": d.name,
        "description": d.description,
        "created_at": d.created_at,
        "object_key": d.object_key or None,
        "sha256": d.sha256 or None,
        "size_bytes": d.size_bytes or None,
        "metadata": json.loads(d.metadata) if d.metadata else None,
    }
