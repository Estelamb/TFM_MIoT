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
_COMPONENTS_CONFIG_PATH = _CONFIG_DIR / "components_config.yaml"


# ── Main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    # Resolve all config values from environment variables or defaults
    device_id          = os.environ.get("AURA_DEVICE_ID",          "dev-device-001")
    mqtt_host          = os.environ.get("AURA_MQTT_HOST",          "localhost")
    mqtt_port          = int(os.environ.get("AURA_MQTT_PORT",      "1883"))
    reconnect_s        = int(os.environ.get("AURA_RECONNECT_S",    "5"))
    telemetry_interval = float(os.environ.get("AURA_TELEMETRY_INTERVAL", "10"))
    inference_interval = float(os.environ.get("AURA_INFERENCE_INTERVAL", "0.1"))
    work_dir           = Path(os.environ.get("AURA_WORK_DIR",      "/tmp/aura"))
    log_level          = os.environ.get("AURA_LOG_LEVEL",          "INFO")
    primary_camera_id = os.environ.get("AURA_PRIMARY_CAMERA")
    if not primary_camera_id:
        peripherals_env = os.environ.get("AURA_PERIPHERALS")
        if peripherals_env:
            try:
                import json
                if peripherals_env.strip().startswith("["):
                    periphs = json.loads(peripherals_env)
                else:
                    periphs = [p.strip() for p in peripherals_env.split(",") if p.strip()]
                cam_ids = [p for p in periphs if "camera" in p.lower()]
                if cam_ids:
                    primary_camera_id = cam_ids[0]
            except Exception:
                pass
    if not primary_camera_id:
        primary_camera_id = "camera_0"
    coordinates_raw    = os.environ.get("AURA_COORDINATES",        "[-3.6294, 40.3897]")

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

    # Save active configuration to device_config.yaml
    active_config = {
        "device_id": device_id,
        "mqtt_host": mqtt_host,
        "mqtt_port": mqtt_port,
        "mqtt_reconnect_interval_s": reconnect_s,
        "hardware_type": os.environ.get("AURA_HARDWARE_TYPE", "rpi"),
        "telemetry_interval_s": telemetry_interval,
        "inference_interval_s": inference_interval,
        "work_dir": str(work_dir),
        "log_level": log_level,
        "primary_camera_id": primary_camera_id,
        "coordinates": coordinates,
    }
    try:
        with open(_CONFIG_DIR / "device_config.yaml", "w", encoding="utf-8") as f:
            yaml.safe_dump(active_config, f, default_flow_style=False)
            logger.info("Active configuration saved to device_config.yaml")
    except Exception as exc:
        logger.warning(f"Could not save active configuration to device_config.yaml: {exc}")

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
        db_path=work_dir / f"mqtt_buffer_{device_id}.db",
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
