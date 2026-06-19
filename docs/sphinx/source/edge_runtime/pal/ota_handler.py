"""
PAL — OTA Handler
==================
Responsible for downloading and validating Over-The-Air deployment
artefacts (model + user script) sent via MQTT ``deploy`` commands.

Workflow
--------
1. Receive a ``deploy`` payload with model URL + SHA-256 and script
   URL + SHA-256.
2. Stream-download each artefact to the work directory.
3. Verify the SHA-256 digest of each downloaded file.
4. Call ``aura_hw.load_model()`` with the new model path.
5. Hot-reload the user script module.
6. Update the in-memory deployment state and notify via MQTT events.

On any failure the partial state is **not** committed — the previous
model and script remain active.
"""
from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import logging
import types
from pathlib import Path
from typing import Callable, Any

import httpx

logger = logging.getLogger(__name__)

# Callback types
EventPublisher = Callable[[str], None]  # publish_event("deploy_ack", ...)


class OTAHandler:
    """Handles OTA deployment of model + script artefacts.

    Parameters
    ----------
    work_dir:
        Directory where artefacts are stored on disk.
    on_event:
        Async callable used to publish MQTT events. Signature:
        ``async def on_event(event: str, **extra) -> None``
    on_deploy_success:
        Async callable invoked after a successful deploy. Receives the
        new deployment state dict.
    """

    def __init__(
        self,
        work_dir: Path,
        on_event: Callable,
        on_deploy_success: Callable,
        device_manager: Any = None,
    ) -> None:
        self._work_dir = work_dir
        self._work_dir.mkdir(parents=True, exist_ok=True)
        self._on_event = on_event
        self._on_deploy_success = on_deploy_success
        self._device_manager = device_manager

        # Paths for the active artefacts on disk
        self._model_path = work_dir / "model"
        self._script_path = work_dir / "script.py"

    # ── Public API ─────────────────────────────────────────────────────────

    async def handle_deploy(self, payload: dict) -> None:
        """Process a ``deploy`` command payload.

        Expected payload keys
        ---------------------
        deployment_id : str
        model_url     : str
        model_sha256  : str
        script_url    : str
        script_sha256 : str
        model_id      : str  (optional)
        script_id     : str  (optional)
        """
        dep_id    = payload["deployment_id"]
        model_url = payload["model_url"]
        model_sha = payload["model_sha256"]
        script_url = payload["script_url"]
        script_sha = payload["script_sha256"]
        model_id  = payload.get("model_id", "")
        script_id = payload.get("script_id", "")

        logger.info(f"[{dep_id}] OTA deploy started")

        try:
            # 1. Download model
            logger.info(f"[{dep_id}] Downloading model from {model_url}")
            await self._download(model_url, self._model_path)
            self._verify_sha256(self._model_path, model_sha, "model")

            # 2. Download script
            logger.info(f"[{dep_id}] Downloading script from {script_url}")
            await self._download(script_url, self._script_path)
            self._verify_sha256(self._script_path, script_sha, "script")

            # 3. Load new model into HAL
            from aura_hw import load_model, unload_model
            logger.info(f"[{dep_id}] Loading model into HAL backend")
            unload_model()
            load_model(str(self._model_path))

            # 4. Hot-reload user script
            logger.info(f"[{dep_id}] Reloading user script")
            script_module = self._load_script(self._script_path)

            # 5. Notify success
            new_state = {
                "active_deployment_id": dep_id,
                "active_model_id": model_id,
                "active_script_id": script_id,
                "script_module": script_module,
                "model_path": str(self._model_path),
            }
            res = self._on_deploy_success(new_state)
            if res is not None and (asyncio.iscoroutine(res) or hasattr(res, "__await__")):
                await res
            await self._on_event("deploy_ack", deployment_id=dep_id)
            logger.info(f"[{dep_id}] OTA deploy completed successfully")

        except Exception as exc:  # noqa: BLE001
            logger.error(f"[{dep_id}] OTA deploy failed: {exc}")
            await self._on_event(
                "deploy_failed", deployment_id=dep_id, error=str(exc)
            )

    async def handle_update_libraries(self, payload: dict) -> None:
        """Process an ``update_libraries`` command payload.

        Expected payload keys
        ---------------------
        libraries_url     : str
        libraries_sha256  : str
        """
        lib_url = payload["libraries_url"]
        lib_sha = payload["libraries_sha256"]

        logger.info("OTA dynamic hardware libraries update started")
        temp_zip = self._work_dir / "libraries_temp.zip"

        try:
            # 1. Download libraries zip
            logger.info(f"Downloading libraries zip from {lib_url}")
            await self._download(lib_url, temp_zip)
            self._verify_sha256(temp_zip, lib_sha, "libraries_zip")

            # 2. Extract zip into the local hardware directory
            import zipfile
            import shutil
            from aura_hw.loader import get_hardware_dir

            hw_dir = get_hardware_dir()
            logger.info(f"Extracting libraries to hardware directory: {hw_dir}")

            # For safety, clean existing sensors, actuators, and hw_arch subdirs
            for subdir in ("sensors", "actuators", "hw_arch"):
                sub_path = hw_dir / subdir
                if sub_path.exists():
                    shutil.rmtree(sub_path)

            # Extract zip
            hw_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(temp_zip, "r") as zip_ref:
                zip_ref.extractall(hw_dir)

            # Re-open any device backends that were closed or failed at startup
            if self._device_manager:
                logger.info("Re-opening device backends after library update...")
                self._device_manager.open_all()

            # 3. Notify success
            await self._on_event("update_libraries_ack", libraries_sha256=lib_sha)
            logger.info("OTA dynamic hardware libraries update completed successfully")

        except Exception as exc:
            logger.error(f"OTA dynamic hardware libraries update failed: {exc}")
            await self._on_event("update_libraries_failed", error=str(exc))
        finally:
            if temp_zip.exists():
                try:
                    temp_zip.unlink()
                except OSError:
                    pass

    # ── Internal helpers ────────────────────────────────────────────────────

    @staticmethod
    async def _download(url: str, dest: Path) -> None:
        """Stream-download *url* to *dest* using chunked I/O."""
        import os
        import socket
        from urllib.parse import urlparse, urlunparse
        
        headers = {}
        parsed = urlparse(url)
        
        # Check if the URL points to a standard local/internal development address
        if parsed.hostname in ("localhost", "127.0.0.1", "minio"):
            # Check if internal 'minio' hostname is resolvable (true in platform docker network)
            use_minio = False
            try:
                socket.gethostbyname("minio")
                use_minio = True
            except socket.gaierror:
                pass
                
            target_host = "minio" if use_minio else os.environ.get("AURA_MQTT_HOST", "localhost")
            new_netloc = f"{target_host}:{parsed.port}" if parsed.port else target_host
            
            # Always preserve the original signed Host header for signature validation
            headers["Host"] = parsed.netloc
                
            parsed = parsed._replace(netloc=new_netloc)
            url = urlunparse(parsed)
            logger.info(f"Redirected local download URL target to: {url}")

        async with httpx.AsyncClient(
            timeout=120.0, follow_redirects=True
        ) as http:
            async with http.stream("GET", url, headers=headers) as response:
                response.raise_for_status()
                with open(dest, "wb") as fh:
                    async for chunk in response.aiter_bytes(65_536):
                        fh.write(chunk)
        logger.debug(f"Downloaded {url} → {dest} ({dest.stat().st_size} bytes)")

    @staticmethod
    def _sha256(path: Path) -> str:
        """Return the SHA-256 hex digest of the file at *path*."""
        digest = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65_536), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _verify_sha256(self, path: Path, expected: str, label: str) -> None:
        """Raise :exc:`ValueError` if the file digest does not match *expected*.

        Parameters
        ----------
        path:
            Local file to verify.
        expected:
            Expected lowercase hex SHA-256 digest.
        label:
            Human-readable label used in error messages (e.g. ``"model"``).
        """
        actual = self._sha256(path)
        if actual != expected.lower():
            raise ValueError(
                f"{label} SHA-256 mismatch — "
                f"expected {expected}, got {actual}"
            )
        logger.debug(f"{label} SHA-256 OK: {actual}")

    @staticmethod
    def _load_script(path: Path) -> types.ModuleType:
        """Import *path* as a Python module and return it.

        The module is loaded under the fixed name ``user_script`` so
        that hot-reloading a new script replaces the previous one.
        """
        spec = importlib.util.spec_from_file_location("user_script", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load script from {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        return module
