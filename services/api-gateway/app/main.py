"""API Gateway entry point.

FastAPI application that acts as the single HTTP entry point for the
frontend. Authenticates requests with JWT and proxies them to the
appropriate downstream gRPC service. Handles multipart file uploads
directly to MinIO to avoid passing large binaries through gRPC.
"""
import logging, sys
from contextlib import asynccontextmanager
sys.path.insert(0, "/app")

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm

from app.auth.jwt import create_token, DEMO_USER
from app.config import get_settings
from app.stubs import init_stubs
from app.routers import devices, models, scripts, deployments, monitoring
from shared.utils.logging import configure_logging
from shared.utils.minio import init_minio, ensure_buckets

s = get_settings()
configure_logging("api-gateway", s.log_level)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_stubs()
    init_minio(
        endpoint=s.minio_endpoint,
        access_key=s.minio_access_key,
        secret_key=s.minio_secret_key,
        secure=s.minio_secure,
        buckets={
            "models":   s.minio_bucket_models,
            "compiled": s.minio_bucket_compiled,
            "scripts":  s.minio_bucket_scripts,
        },
    )
    await ensure_buckets()
    logging.getLogger("api-gateway").info("API Gateway ready")
    yield

app = FastAPI(title="AURA Platform API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/auth/token")
async def login(form: OAuth2PasswordRequestForm = Depends()):
    if form.username != DEMO_USER["username"] or form.password != DEMO_USER["password"]:
        raise HTTPException(401, "Invalid credentials")
    return {"access_token": create_token(form.username), "token_type": "bearer"}

@app.get("/health")
async def health():
    return {"status": "ok", "platform": "AURA"}

app.include_router(devices.router)
app.include_router(models.router)
app.include_router(scripts.router)
app.include_router(deployments.router)
app.include_router(monitoring.router)
