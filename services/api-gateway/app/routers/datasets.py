import uuid
from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.auth.jwt import verify_token
from app.stubs import get_stub
from shared.proto_gen import ai_pb2
from shared.utils.minio import upload_bytes

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.post("", status_code=201)
async def create_dataset(
    name: str = Form(...),
    description: str = Form(""),
    _=Depends(verify_token),
):
    d = await get_stub("ai").UploadDataset(
        ai_pb2.UploadDatasetRequest(name=name, description=description)
    )
    return {
        "id": d.id,
        "name": d.name,
        "description": d.description,
        "created_at": d.created_at,
    }


@router.get("")
async def list_datasets(_=Depends(verify_token)):
    r = await get_stub("ai").ListDatasets(ai_pb2.ListDatasetsRequest())
    return [
        {
            "id": d.id,
            "name": d.name,
            "description": d.description,
            "created_at": d.created_at,
        }
        for d in r.datasets
    ]


@router.get("/{dataset_id}")
async def get_dataset(dataset_id: str, _=Depends(verify_token)):
    d = await get_stub("ai").GetDataset(ai_pb2.GetDatasetRequest(id=dataset_id))
    return {
        "id": d.id,
        "name": d.name,
        "description": d.description,
        "created_at": d.created_at,
    }


@router.delete("/{dataset_id}", status_code=204)
async def delete_dataset(dataset_id: str, _=Depends(verify_token)):
    await get_stub("ai").DeleteDataset(ai_pb2.DeleteDatasetRequest(id=dataset_id))


@router.post("/{dataset_id}/versions", status_code=201)
async def upload_dataset_version(
    dataset_id: str,
    version: str = Form(...),
    description: str = Form(""),
    file: UploadFile = File(...),
    _=Depends(verify_token),
):
    data = await file.read()
    object_key = f"{dataset_id}/{version}/{uuid.uuid4()}-{file.filename or 'dataset.bin'}"
    sha = await upload_bytes("datasets", object_key, data)

    v = await get_stub("ai").UploadDatasetVersion(
        ai_pb2.UploadDatasetVersionRequest(
            dataset_id=dataset_id,
            version=version,
            description=description,
            object_key=object_key,
            sha256=sha,
            size_bytes=len(data),
        )
    )
    return {
        "id": v.id,
        "dataset_id": v.dataset_id,
        "version": v.version,
        "description": v.description,
        "object_key": v.object_key,
        "sha256": v.sha256,
        "size_bytes": v.size_bytes,
        "model_ids": list(v.model_ids),
        "created_at": v.created_at,
    }


@router.get("/{dataset_id}/versions")
async def list_dataset_versions(dataset_id: str, _=Depends(verify_token)):
    r = await get_stub("ai").ListDatasetVersions(
        ai_pb2.ListDatasetVersionsRequest(dataset_id=dataset_id)
    )
    return [
        {
            "id": v.id,
            "dataset_id": v.dataset_id,
            "version": v.version,
            "description": v.description,
            "object_key": v.object_key,
            "sha256": v.sha256,
            "size_bytes": v.size_bytes,
            "model_ids": list(v.model_ids),
            "created_at": v.created_at,
        }
        for v in r.versions
    ]


@router.get("/versions/{version_id}")
async def get_dataset_version(version_id: str, _=Depends(verify_token)):
    v = await get_stub("ai").GetDatasetVersion(ai_pb2.GetDatasetVersionRequest(id=version_id))
    return {
        "id": v.id,
        "dataset_id": v.dataset_id,
        "version": v.version,
        "description": v.description,
        "object_key": v.object_key,
        "sha256": v.sha256,
        "size_bytes": v.size_bytes,
        "model_ids": list(v.model_ids),
        "created_at": v.created_at,
    }
