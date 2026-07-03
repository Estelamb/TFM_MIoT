"""
Abstract compiler interface for the AURA compilation service.

Each hardware target has a concrete :class:`CompilerBase` subclass that
handles the full pipeline from downloading the source ``.pt`` model to
uploading the compiled artefact to MinIO.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal


@dataclass
class CompilationResult:
    """Result object returned by every compiler implementation.

    Attributes:
        success:         Whether compilation completed without errors.
        compiled_key:    MinIO object key of the compiled artefact,
                 e.g. ``"{model_id}/model.hef"``. Empty on failure.
        compiled_sha256: Hex SHA-256 digest of the uploaded artefact.
                 Empty on failure.
        error:           Human-readable error message. Empty on success.
    """
    success: bool
    compiled_key: str = ""
    compiled_sha256: str = ""
    error: str = ""


class CompilerBase(ABC):
    """Abstract base class for hardware-specific model compilers.

    Subclasses implement :meth:`compile` and are registered in the
    ``COMPILER_REGISTRY`` dict inside
    :mod:`~app.grpc_handlers.compilation_handler`.

    Example registry entry::

        COMPILER_REGISTRY = {
            "hailo8": HailoCompiler(bucket_models, bucket_compiled),
        }
    """

    EXECUTION_STRATEGY: Literal["docker", "python"] = "python"
    """The execution strategy required by the compiler:
    - 'docker': compiler runs inside an external Docker container.
    - 'python': compiler runs inside the compilation-service process.
    """

    DOCKER_IMAGE: str = ""
    """The Docker image tag required for docker-based compilation.
    Should be an empty string for python-based execution.
    """

    OUTPUT_FORMAT: str = ""
    """The extension/format of the compiled artifact, e.g. '.hef', '.zip'."""

    SUPPORTED_HARDWARE: list[str] = []
    """A list of hardware_type strings supported by this compiler."""

    @abstractmethod
    async def compile(
        self,
        model_id: str,
        source_key: str,
        num_classes: int,
        class_names: list[str],
        hardware_type: str,
        dataset_id: str,
        dataset_key: str,
        base_architecture: str = "",
        input_size: str = "",
    ) -> CompilationResult:
        """Compile a ``.pt`` model for a specific hardware target.

        Implementations should:

        1. Download the source model from MinIO using ``source_key``.
        2. Run the hardware-specific compilation pipeline.
        3. Upload the compiled artefact to MinIO.
        4. Return a :class:`CompilationResult` describing the outcome.

        Args:
            model_id:      UUID of the model record in the database.
            source_key:    MinIO object key of the source ``.pt`` file.
            num_classes:   Number of output classes in the model.
            class_names:   Ordered list of class label strings.
            hardware_type: Target hardware identifier, e.g. ``"hailo8"``.

        Returns:
            A :class:`CompilationResult` with ``success=True`` and the
            MinIO key / SHA-256 of the compiled artefact on success, or
            ```success=False``` with a descriptive ``error`` string on failure.
        """
        ...

    async def log_progress(self, model_id: str, message: str) -> None:
        """Publish a compilation log message to Redis for real-time frontend streaming."""
        import logging
        logger = logging.getLogger(__name__)
        redis = getattr(self, "redis_client", None)
        if redis:
            try:
                redis_list = f"train_logs:{model_id}_list"
                redis_channel = f"train_logs:{model_id}"
                await redis.rpush(redis_list, message)
                await redis.ltrim(redis_list, -5000, -1)
                await redis.expire(redis_list, 86400)
                await redis.publish(redis_channel, message)
            except Exception as e:
                logger.warning(f"Failed to publish compilation log to redis: {e}")

    async def run_subprocess_with_logs(self, model_id: str, cmd: list[str], **kwargs) -> int:
        """Execute a subprocess and stream its combined stdout/stderr to Redis in real-time, checking for cancellation."""
        import asyncio
        import logging
        logger = logging.getLogger(__name__)
        
        redis = getattr(self, "redis_client", None)
        redis_list = f"train_logs:{model_id}_list"
        redis_channel = f"train_logs:{model_id}"
        cancel_key = f"cancel:compile:{model_id}"
        
        # Merge stderr into stdout
        kwargs["stdout"] = asyncio.subprocess.PIPE
        kwargs["stderr"] = asyncio.subprocess.STDOUT
        
        process = await asyncio.create_subprocess_exec(*cmd, **kwargs)
        
        cancellation_task = None
        if redis:
            async def check_cancel():
                try:
                    while True:
                        if await redis.exists(cancel_key):
                            logger.info(f"Cancellation requested for compilation {model_id}. Terminating subprocess...")
                            try:
                                process.terminate()
                                await asyncio.sleep(1)
                                process.kill()
                            except ProcessLookupError:
                                pass
                            break
                        await asyncio.sleep(2)
                except asyncio.CancelledError:
                    pass
            cancellation_task = asyncio.create_task(check_cancel())

        try:
            while True:
                line_bytes = await process.stdout.readline()
                if not line_bytes:
                    break
                line_str = line_bytes.decode('utf-8', errors='replace').strip()
                if line_str:
                    logger.info(f"[{model_id}] {line_str}")
                    if redis:
                        try:
                            await redis.rpush(redis_list, line_str)
                            await redis.ltrim(redis_list, -5000, -1)
                            await redis.expire(redis_list, 86400)
                            await redis.publish(redis_channel, line_str)
                        except Exception as e:
                            logger.warning(f"Failed to publish subprocess log to redis: {e}")
        except Exception as e:
            logger.error(f"Error streaming subprocess logs: {e}")
            if redis:
                await redis.rpush(redis_list, f"Error streaming logs: {e}")
                await redis.publish(redis_channel, f"Error streaming logs: {e}")
        finally:
            if cancellation_task:
                cancellation_task.cancel()
                try:
                    await cancellation_task
                except asyncio.CancelledError:
                    pass
            await process.wait()
            
        return process.returncode
