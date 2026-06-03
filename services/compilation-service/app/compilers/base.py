"""
Abstract compiler interface for the AURA compilation service.

Each hardware target has a concrete :class:`CompilerBase` subclass that
handles the full pipeline from downloading the source ``.pt`` model to
uploading the compiled artefact to MinIO.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


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

    @abstractmethod
    async def compile(
        self,
        model_id: str,
        source_key: str,
        num_classes: int,
        class_names: list[str],
        hardware_type: str,
        dataset_version_id: str,
        dataset_key: str,
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
            ``success=False`` with a descriptive ``error`` string on failure.
        """
        ...
