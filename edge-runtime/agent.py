"""
AURA Edge Agent — Entrypoint
=============================
Minimal entrypoint that wires together the PAL components:

* :class:`~pal.comm_client.CommunicationClient` — MQTT publish/subscribe
* :class:`~pal.ota_handler.OTAHandler`          — OTA deploy handler
* :class:`~pal.orchestrator.Orchestrator`        — inference + telemetry loops
* :class:`~aura_hw.device_manager.DeviceManager` — connected device backends

Configuration (priority order)
-------------------------------
1. Environment variables
2. ``config/device_config.yaml``
3. Built-in defaults

MQTT Topics
-----------
Subscribe:  device/{DEVICE_ID}/commands
Publish:    device/{DEVICE_ID}/events
            device/{DEVICE_ID}/telemetry
            device/{DEVICE_ID}/inference
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from pathlib import Path

import yaml

# ── Logging ──────────────────────────────────────────────────────────────────

def _setup_logging(level_str: str) -> None:
    level = getattr(logging, level_str.upper(), logging.INFO)
    logging.basicConfig(
        stream=sys.stdout,
        level=level,
        format="%(asctime)s [edge-agent] %(levelname)s — %(message)s",
    )

# ── Config loading ────────────────────────────────────────────────────────────

_CONFIG_DIR = Path(__file__).parent / "config"
_DEVICE_CONFIG_PATH  = _CONFIG_DIR / "device_config.yaml"
_COMPONENTS_CONFIG_PATH = _CONFIG_DIR / "components_config.yaml"


def _load_device_config() -> dict:
    """Load device_config.yaml, falling back to an empty dict on error."""
    try:
        with open(_DEVICE_CONFIG_PATH) as fh:
            return yaml.safe_load(fh) or {}
    except FileNotFoundError:
        return {}
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).warning(
            f"Could not read device_config.yaml: {exc}"
        )
        return {}


def _cfg(env_key: str, yaml_key: str, default: str, file_cfg: dict) -> str:
    """Resolve a config value: env var > YAML > default."""
    return os.environ.get(env_key) or str(file_cfg.get(yaml_key, default))


# ── Main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    file_cfg = _load_device_config()

    # Resolve all config values
    device_id          = _cfg("AURA_DEVICE_ID",         "device_id",                  "dev-device-001", file_cfg)
    mqtt_host          = _cfg("AURA_MQTT_HOST",         "mqtt_host",                  "localhost",      file_cfg)
    mqtt_port          = int(_cfg("AURA_MQTT_PORT",     "mqtt_port",                  "1883",           file_cfg))
    reconnect_s        = int(_cfg("AURA_RECONNECT_S",   "mqtt_reconnect_interval_s",  "5",              file_cfg))
    telemetry_interval = float(_cfg("AURA_TELEMETRY_INTERVAL", "telemetry_interval_s","10",             file_cfg))
    inference_interval = float(_cfg("AURA_INFERENCE_INTERVAL", "inference_interval_s","0.1",            file_cfg))
    work_dir           = Path(_cfg("AURA_WORK_DIR",     "work_dir",                   "/tmp/aura",      file_cfg))
    log_level          = _cfg("AURA_LOG_LEVEL",         "log_level",                  "INFO",           file_cfg)
    primary_camera_id  = _cfg("AURA_PRIMARY_CAMERA",    "primary_camera_id",          "camera_0",       file_cfg)
    coordinates_raw    = _cfg("AURA_COORDINATES",       "coordinates",                "[-3.7038, 40.4168]", file_cfg)

    # Parse coordinates
    import json
    try:
        coordinates = json.loads(coordinates_raw) if isinstance(coordinates_raw, str) else coordinates_raw
        if not isinstance(coordinates, list) or len(coordinates) != 2:
            coordinates = [-3.7038, 40.4168]
    except Exception:
        coordinates = [-3.7038, 40.4168]

    _setup_logging(log_level)
    logger = logging.getLogger(__name__)

    # Register signal handlers for graceful shutdown on SIGTERM/SIGINT
    import signal
    def handle_sigterm(*args):
        logger.info("Signal received — exiting gracefully")
        sys.exit(0)

    try:
        signal.signal(signal.SIGTERM, handle_sigterm)
        signal.signal(signal.SIGINT, handle_sigterm)
    except ValueError:
        pass

    work_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"AURA Edge Agent starting — device_id={device_id}")

    # ── Instantiate PAL + HAL components ─────────────────────────────────
    from pal.comm_client import CommunicationClient
    from pal.ota_handler import OTAHandler
    from pal.orchestrator import Orchestrator
    from aura_hw.device_manager import DeviceManager

    start_time = time.monotonic()

    # Device manager — opens peripheral backends from components_config.yaml
    device_manager = DeviceManager(_COMPONENTS_CONFIG_PATH)
    device_manager.open_all()
    logger.info(
        f"Device manager initialised: "
        f"components={device_manager.list_components()}"
    )

    comm = CommunicationClient(
        device_id=device_id,
        host=mqtt_host,
        port=mqtt_port,
        reconnect_interval_s=reconnect_s,
    )

    orchestrator = Orchestrator(
        comm_client=comm,
        device_manager=device_manager,
        work_dir=work_dir,
        inference_interval_s=inference_interval,
        telemetry_interval_s=telemetry_interval,
        start_time=start_time,
        primary_camera_id=primary_camera_id,
        coordinates=coordinates,
    )

    ota = OTAHandler(
        work_dir=work_dir,
        on_event=comm.publish_event,
        on_deploy_success=orchestrator.apply_deployment,
        device_manager=device_manager,
    )

    # ── Register MQTT command handlers ────────────────────────────────────
    comm.register_command_handler("deploy", ota.handle_deploy)
    comm.register_command_handler("update_libraries", ota.handle_update_libraries)

    # ── Launch concurrent async tasks ─────────────────────────────────────
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(comm.run(),                    name="mqtt-loop")
            tg.create_task(orchestrator.run_inference_loop(), name="inference-loop")
            tg.create_task(orchestrator.run_telemetry_loop(), name="telemetry-loop")
    finally:
        # Ensure devices are cleanly closed on exit
        logger.info("Shutting down — closing all devices")
        device_manager.close_all()

        # Publish offline status to the broker before exiting (handles clean exit status sync)
        logger.info("Publishing offline status to broker...")
        import json
        try:
            import paho.mqtt.client as mqtt
            client = mqtt.Client()
            client.connect(mqtt_host, mqtt_port, 60)
            client.publish(f"device/{device_id}/status", json.dumps({"status": "offline"}), retain=True)
            client.disconnect()
            logger.info("Offline status published successfully.")
        except Exception as e:
            logger.warning(f"Could not publish offline status on exit: {e}")


if __name__ == "__main__":
    asyncio.run(main())
