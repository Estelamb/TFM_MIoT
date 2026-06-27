"""
PAL — Orchestrator
===================
Central coordinator of the edge agent.  Manages two independent async
loops and maintains consistent device state across both.

Inference Loop
--------------
Runs every ``inference_interval_s`` seconds (default 0.1 s).

* Requires a model to be loaded (via OTA deploy).  If no model is
  loaded, the tick is **skipped silently** (warning logged, nothing
  published).
* Captures a frame from the primary camera via the :class:`DeviceManager`
  (component ``camera_0``) and passes it as input to the inference backend.
* Stores the result in ``_last_inference`` for the telemetry loop.
* Publishes result + timestamp to ``device/{id}/inference``.
* Updates ``local_state.json``.

Telemetry Loop
--------------
Runs every ``telemetry_interval_s`` seconds (default 10 s).

* Collects system metrics (CPU, RAM, temperature via psutil).
* Reads all connected device states from :class:`DeviceManager`.
* Calls the user script ``run(raw_input)`` if one is loaded, passing
  the latest captured frame as ``raw_input``.
* Publishes the combined payload to ``device/{id}/telemetry``.
* Updates ``local_state.json``.

State Management
----------------
The orchestrator owns the single source of truth for deployment state.
The OTAHandler calls ``apply_deployment()`` after a successful download.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil

logger = logging.getLogger(__name__)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Orchestrator:
    """Manages inference and telemetry loops plus deployment state.

    Parameters
    ----------
    comm_client:
        :class:`~pal.comm_client.CommunicationClient` used to publish
        inference and telemetry messages.
    device_manager:
        :class:`~aura_hw.device_manager.DeviceManager` managing connected
        peripheral backends (cameras, sensors).
    work_dir:
        Working directory where ``local_state.json`` is written.
    inference_interval_s:
        Seconds between inference passes.
    telemetry_interval_s:
        Seconds between telemetry publications.
    start_time:
        Monotonic timestamp recorded at agent startup (for uptime).
    primary_camera_id:
        Component ID of the camera used to supply frames to the inference
        loop (default ``"camera_0"``).
    """

    def __init__(
        self,
        comm_client: Any,
        device_manager: Any,
        work_dir: Path,
        inference_interval_s: float = 0.1,
        telemetry_interval_s: float = 10.0,
        start_time: float | None = None,
        primary_camera_id: str = "camera_0",
        coordinates: list[float] | None = None,
    ) -> None:
        self._comm = comm_client
        self._device_manager = device_manager
        self._work_dir = work_dir
        self._inference_interval = inference_interval_s
        self._telemetry_interval = telemetry_interval_s
        self._start_time = start_time or time.monotonic()
        self._primary_camera_id = primary_camera_id
        self._coordinates = coordinates

        # ── Deployment state ──────────────────────────────────────────────
        self._active_deployment_id: str = ""
        self._active_model_id: str = ""
        self._active_script_id: str = ""
        self._script_module: types.ModuleType | None = None

        # ── Last inference result (shared between loops) ───────────────────
        self._inference_latencies: list[float] = []
        self._last_frame: Any = None
        self._last_inference: Any = None
        self._last_inference_ts: str | None = None

        # ── Timestamps ────────────────────────────────────────────────────
        self._last_telemetry_ts: str | None = None

    # ── Public API ──────────────────────────────────────────────────────────

    def apply_deployment(self, state: dict) -> None:
        """Atomically update deployment state after a successful OTA.

        Called by :class:`~pal.ota_handler.OTAHandler` after all
        artefacts have been verified and the HAL model is loaded.

        Parameters
        ----------
        state:
            Dict with keys: ``active_deployment_id``, ``active_model_id``,
            ``active_script_id``, ``script_module``.
        """
        self._active_deployment_id = state.get("active_deployment_id", "")
        self._active_model_id = state.get("active_model_id", "")
        self._active_script_id = state.get("active_script_id", "")
        self._script_module = state.get("script_module")
        logger.info(
            f"Deployment applied: id={self._active_deployment_id} "
            f"model={self._active_model_id} script={self._active_script_id}"
        )

    async def run_inference_loop(self) -> None:
        """Inference loop — runs until cancelled."""
        logger.info(
            f"Inference loop started (interval={self._inference_interval}s)"
        )
        while True:
            try:
                await self._inference_tick()
            except asyncio.CancelledError:
                logger.info("Inference loop cancelled")
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Inference tick error: {exc}")
            await asyncio.sleep(self._inference_interval)

    async def run_telemetry_loop(self) -> None:
        """Telemetry loop — runs until cancelled."""
        logger.info(
            f"Telemetry loop started (interval={self._telemetry_interval}s)"
        )
        while True:
            try:
                await self._telemetry_tick()
            except asyncio.CancelledError:
                logger.info("Telemetry loop cancelled")
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Telemetry tick error: {exc}")
            await asyncio.sleep(self._telemetry_interval)

    # ── Loop internals ────────────────────────────────────────────────────────

    async def _inference_tick(self) -> None:
        """Single inference pass.

        Skips silently if no model is loaded yet.
        """
        from aura_hw import execute_inference, get_hardware_info

        hw = get_hardware_info()
        if not hw["model_loaded"]:
            logger.debug("Inference tick skipped — no model loaded")
            return

        ts = _utcnow_iso()

        # Capture frame from primary camera (if available)
        frame = await asyncio.get_event_loop().run_in_executor(
            None, self._capture_frame
        )
        self._last_frame = frame

        # Run inference (in thread executor to avoid blocking the event loop)
        t0 = time.perf_counter()
        if self._script_module is not None and hasattr(self._script_module, "run"):
            run_fn = getattr(self._script_module, "run")
            result = await asyncio.get_event_loop().run_in_executor(
                None, run_fn, frame
            )
        else:
            result = await asyncio.get_event_loop().run_in_executor(
                None, execute_inference, frame
            )
        latency_ms = (time.perf_counter() - t0) * 1000.0
        self._inference_latencies.append(latency_ms)
        if len(self._inference_latencies) > 100:
            self._inference_latencies.pop(0)
        self._last_inference = result
        self._last_inference_ts = ts

        payload = {
            "ts": ts,
            "hardware_type": hw["hardware_type"],
            "model_loaded": True,
            "deployment_id": self._active_deployment_id,
            "result": _serialise(result),
        }
        await self._comm.publish_inference(payload)
        self._persist_state()

    async def _telemetry_tick(self) -> None:
        """Single telemetry pass: system metrics + device states + user script."""
        from aura_hw import get_hardware_info

        from aura_hw.loader import get_libraries_hash

        ts = _utcnow_iso()
        mem = psutil.virtual_memory()
        hw = get_hardware_info()

        if self._inference_latencies:
            avg_latency = sum(self._inference_latencies) / len(self._inference_latencies)
            self._inference_latencies.clear()
        else:
            avg_latency = 0.0

        # Query active GPS sensors in DeviceManager to update local coordinates
        for dev_id in self._device_manager.list_components():
            try:
                dev = self._device_manager.get_device(dev_id)
                if dev.device_type == "gps":
                    coords = dev.measure()
                    if isinstance(coords, list) and len(coords) == 2:
                        self._coordinates = coords
                        break
            except Exception as e:
                logger.warning(f"Failed to read GPS coordinates from device '{dev_id}': {e}")

        payload: dict[str, Any] = {
            "ts": ts,
            "cpu_percent": psutil.cpu_percent(interval=None),
            "ram_percent": mem.percent,
            "ram_used_mb": round(mem.used / 1024 / 1024, 1),
            "uptime_s": round(time.monotonic() - self._start_time, 1),
            "hardware_type": hw["hardware_type"],
            "model_loaded": hw["model_loaded"],
            "backend": hw["backend"],
            "active_deployment_id": self._active_deployment_id,
            "active_model_id": self._active_model_id,
            "active_script_id": self._active_script_id,
            "libraries_hash": get_libraries_hash(),
            "coordinates": self._coordinates,
            "latency_ms": round(avg_latency, 2),
        }

        # Temperature sensors (not available on all platforms)
        temps = _read_temperatures()
        if temps:
            payload["temperatures"] = temps

        # Connected device states from DeviceManager
        payload["devices"] = self._device_manager.get_all_info()

        # Execute user script if one is loaded
        script_output = await self._run_user_script()
        if script_output is not None:
            payload["script_output"] = _serialise(script_output)

        self._last_telemetry_ts = ts
        await self._comm.publish_telemetry(payload)
        self._persist_state()
        logger.debug(f"Telemetry published at {ts}")

    async def _run_user_script(self) -> Any:
        """Invoke ``script_module.run(raw_input)`` in a thread executor.

        The user script imports ``aura_hw`` directly and may call
        ``execute_inference()`` internally.  The latest captured frame
        is passed as ``raw_input`` so the script has access to it.

        Returns ``None`` if no script is loaded or execution fails.
        """
        if self._script_module is None:
            return None
        run_fn = getattr(self._script_module, "run", None)
        if run_fn is None:
            logger.warning("User script has no run() function")
            return None
        raw_input = self._last_frame
        try:
            return await asyncio.get_event_loop().run_in_executor(
                None, run_fn, raw_input
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(f"User script error: {exc}")
            return {"error": str(exc)}

    def _capture_frame(self) -> Any:
        """Capture a frame from the primary camera via DeviceManager.

        Returns ``None`` if the primary camera is not configured or
        frame capture fails.
        """
        try:
            camera = self._device_manager.get_device(self._primary_camera_id)
            return camera.capture_frame()
        except KeyError:
            logger.debug(
                f"Primary camera '{self._primary_camera_id}' not found in DeviceManager"
            )
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Frame capture error: {exc}")
            return None

    # ── State persistence ─────────────────────────────────────────────────────

    def _persist_state(self) -> None:
        """Write the current device state to ``local_state.json``."""
        from aura_hw import get_hardware_info

        hw = get_hardware_info()
        state = {
            "_comment": (
                "Auto-generated by AURA Edge Runtime. "
                "Do not edit manually — it is overwritten on every update."
            ),
            "device_status": "running",
            "active_deployment_id": self._active_deployment_id,
            "active_model_id": self._active_model_id,
            "active_script_id": self._active_script_id,
            "model_loaded": hw["model_loaded"],
            "hardware_type": hw["hardware_type"],
            "backend": hw["backend"],
            "last_inference_ts": self._last_inference_ts,
            "last_telemetry_ts": self._last_telemetry_ts,
            "uptime_s": round(time.monotonic() - self._start_time, 1),
            "components": self._device_manager.get_all_info(),
        }
        state_path = self._work_dir / "local_state.json"
        try:
            state_path.write_text(json.dumps(state, indent=2))
        except OSError as exc:
            logger.warning(f"Could not write local_state.json: {exc}")


# ── Module-level helpers ──────────────────────────────────────────────────────


def _serialise(value: Any) -> Any:
    """Convert numpy arrays / non-serialisable objects to plain Python types."""
    try:
        import numpy as np
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, dict):
            return {k: _serialise(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [_serialise(v) for v in value]
        if isinstance(value, (np.integer, np.floating)):
            return value.item()
    except ImportError:
        pass
    return value


def _read_temperatures() -> dict[str, float]:
    """Read CPU/GPU temperatures via psutil (returns empty dict on failure)."""
    try:
        sensors = psutil.sensors_temperatures()
        if not sensors:
            return {}
        result: dict[str, float] = {}
        for name, entries in sensors.items():
            for entry in entries:
                label = entry.label or name
                result[label] = round(entry.current, 1)
        return result
    except (AttributeError, Exception):  # noqa: BLE001
        return {}
