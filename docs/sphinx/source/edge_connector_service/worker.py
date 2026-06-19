"""
ARQ worker for deployment-service.

Defines compile_and_deploy_job: triggers compilation via compilation-service
gRPC, then waits for the model to become ready by polling Redis (published
by the compilation worker) rather than polling Postgres in a busy loop.
"""
import os
import logging
import asyncio
import json
import aiomqtt
import grpc
import redis.asyncio as aioredis
from arq.connections import RedisSettings

from app.models.orm import Deployment, ModelRef
from app.repositories.deployments import DeploymentRepository
from shared.proto_gen import ai_pb2, ai_pb2_grpc, compilation_pb2, compilation_pb2_grpc
from shared.utils.minio import presigned_url
from app.config import get_settings

logger = logging.getLogger(__name__)


async def compile_and_deploy_job(
    ctx,
    *,
    dep_id,
    model_id,
    device_id,
    script_id,
    hardware_type,
    source_key,
    dataset_id,
    script_key,
    script_sha256,
    base_architecture,
    input_size
):
    try:
        logger.info(f"Asynchronously compiling model {model_id} for device {device_id} (hw: {hardware_type})")
        redis = ctx["redis"]
        
        # Check cancellation before starting
        if await redis.exists(f"cancel:deploy:{dep_id}"):
            logger.info(f"Deployment {dep_id} was cancelled before starting. Deleting from DB...")
            async with ctx["session_factory"]() as s:
                dep = await s.get(Deployment, dep_id)
                if dep:
                    await s.delete(dep)
                    await s.commit()
            await redis.delete(f"cancel:deploy:{dep_id}")
            return
 
        # 1. Fetch dataset details from AI service
        try:
            dv = await ctx["ai_stub"].GetDataset(ai_pb2.GetDatasetRequest(id=dataset_id))
        except Exception as e:
            logger.error(f"Failed to get dataset details for dataset {dataset_id}: {e}")
            async with ctx["session_factory"]() as s:
                dep = await s.get(Deployment, dep_id)
                if dep:
                    await DeploymentRepository(s).mark_failed(dep, f"Failed to retrieve dataset details: {e}")
            return
 
        # Check if compilation is already ready or in progress for this hardware
        skip_compile = False
        async with ctx["session_factory"]() as s:
            model = await s.get(ModelRef, model_id)
            if model and model.hardware_type == hardware_type and model.compile_status in ("compiling", "ready"):
                skip_compile = True
                logger.info(f"Model {model_id} is already {model.compile_status} for {hardware_type}. Skipping CompileModel.")

        if not skip_compile:
            # Delete old redis key before triggering compilation to prevent reading obsolete "ready" state
            await redis.delete(f"model_compile_done:{model_id}")
            # 2. Call compilation service to trigger build
            try:
                comp_res = await ctx["comp_stub"].CompileModel(compilation_pb2.CompileModelRequest(
                    model_id=model_id,
                    source_key=source_key,
                    hardware_type=hardware_type,
                    dataset_id=dataset_id,
                    dataset_key=dv.object_key,
                    base_architecture=base_architecture,
                    input_size=input_size,
                ))
                if comp_res.status == "failed":
                    logger.error(f"Compilation service rejected build: {comp_res.error}")
                    async with ctx["session_factory"]() as s:
                        dep = await s.get(Deployment, dep_id)
                        if dep:
                            await DeploymentRepository(s).mark_failed(dep, f"Compilation failed: {comp_res.error}")
                    return
            except Exception as e:
                logger.error(f"Failed to call compilation service: {e}")
                async with ctx["session_factory"]() as s:
                    dep = await s.get(Deployment, dep_id)
                    if dep:
                        await DeploymentRepository(s).mark_failed(dep, f"Compilation call error: {e}")
                return

        # 3. Poll compilation status from Redis instead of Postgres
        pubsub_key = f"model_compile_done:{model_id}"

        success = False
        error_msg = "Timeout waiting for compilation to finish"

        # Check Redis with sleep, max 2 hours total (7200 seconds)
        deadline = asyncio.get_event_loop().time() + 7200
        while asyncio.get_event_loop().time() < deadline:
            # Check if deployment was cancelled
            if await redis.exists(f"cancel:deploy:{dep_id}"):
                logger.info(f"Deployment {dep_id} was cancelled. Deleting from DB...")
                async with ctx["session_factory"]() as s:
                    dep = await s.get(Deployment, dep_id)
                    if dep:
                        await s.delete(dep)
                        await s.commit()
                await redis.delete(f"cancel:deploy:{dep_id}")
                return

            result = await redis.get(pubsub_key)
            if result:
                result_str = result.decode() if isinstance(result, bytes) else result
                if result_str == "ready":
                    success = True
                    break
                elif result_str.startswith("failed:"):
                    success = False
                    error_msg = result_str[7:]
                    break
            await asyncio.sleep(10)
        else:
            success = False

        if not success:
            logger.error(f"Compilation failed or timed out: {error_msg}")
            async with ctx["session_factory"]() as s:
                dep = await s.get(Deployment, dep_id)
                if dep:
                    await DeploymentRepository(s).mark_failed(dep, error_msg)
            return

        # Fetch model from DB to get compiled_key and compiled_sha256
        compiled_key = ""
        compiled_sha256 = ""
        async with ctx["session_factory"]() as s:
            model = await s.get(ModelRef, model_id)
            if model:
                compiled_key = model.compiled_key
                compiled_sha256 = model.compiled_sha256
            else:
                logger.error(f"Model {model_id} not found in DB after compilation")
                dep = await s.get(Deployment, dep_id)
                if dep:
                    await DeploymentRepository(s).mark_failed(dep, "Model ref not found in DB")
                return

        # Fallback if DB doesn't have details yet
        if not compiled_key:
            try:
                m_details = await ctx["ai_stub"].GetModel(ai_pb2.GetModelRequest(id=model_id))
                compiled_key = m_details.compiled_key
                compiled_sha256 = m_details.compiled_sha256
            except Exception as e:
                logger.exception(f"Failed to fetch model details from AI service: {e}")

        # 4. Compilation successful! Generate URLs and publish MQTT command
        model_url = await presigned_url("compiled", compiled_key)
        script_url = await presigned_url("scripts", script_key)

        command = {
            "command": "deploy",
            "deployment_id": dep_id,
            "model_url": model_url,
            "model_sha256": compiled_sha256,
            "script_url": script_url,
            "script_sha256": script_sha256,
        }

        s_conf = get_settings()
        async with aiomqtt.Client(hostname=s_conf.mqtt_host, port=s_conf.mqtt_port) as client:
            await client.publish(f"device/{device_id}/commands", json.dumps(command))
        
        async with ctx["session_factory"]() as s:
            dep = await s.get(Deployment, dep_id)
            if dep:
                await DeploymentRepository(s).mark_sent(dep)
        logger.info(f"Model compiled successfully. Deploy command sent to device {device_id} for deployment {dep_id}")

    except Exception as e:
        logger.exception(f"Unexpected error in compile & deploy worker: {e}")
        async with ctx["session_factory"]() as s:
            dep = await s.get(Deployment, dep_id)
            if dep:
                await DeploymentRepository(s).mark_failed(dep, f"Internal deploy worker error: {e}")


class WorkerSettings:
    functions = [compile_and_deploy_job]
    redis_settings = RedisSettings.from_dsn(os.environ.get("REDIS_URL", "redis://localhost:6379"))
    queue_name = "deployment_queue"
    max_jobs = 10         # deployments can run concurrently (they mostly wait)
    job_timeout = 14400   # 4 hours max (training + compilation + deploy)
    keep_result = 3600

    @staticmethod
    async def on_startup(ctx):
        from app.config import get_settings
        from shared.utils.minio import init_minio, ensure_buckets
        from shared.utils.database import build_engine, build_session_factory
        from shared.proto_gen import ai_pb2_grpc, compilation_pb2_grpc
        import grpc
        import redis.asyncio as aioredis

        s = get_settings()

        init_minio(s.minio_endpoint, s.minio_access_key, s.minio_secret_key,
                   s.minio_secure, {"compiled": s.minio_bucket_compiled,
                                    "scripts": s.minio_bucket_scripts})

        engine = build_engine(s.postgres_dsn)
        ctx["session_factory"] = build_session_factory(engine)

        ai_channel = grpc.aio.insecure_channel(s.ai_service_grpc)
        comp_channel = grpc.aio.insecure_channel(s.compilation_service_grpc)
        ctx["ai_stub"]   = ai_pb2_grpc.AIServiceStub(ai_channel)
        ctx["comp_stub"] = compilation_pb2_grpc.CompilationServiceStub(comp_channel)
        ctx["ai_channel"]   = ai_channel
        ctx["comp_channel"] = comp_channel

        # Raw Redis client for pub/sub polling
        ctx["redis"] = aioredis.from_url(s.redis_url)

    @staticmethod
    async def on_shutdown(ctx):
        for key in ("ai_channel", "comp_channel"):
            if key in ctx:
                await ctx[key].close()
        if "redis" in ctx:
            await ctx["redis"].close()
