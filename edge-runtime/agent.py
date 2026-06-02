"""
AURA Edge Agent
===============
Comandos MQTT recibidos:  device/{DEVICE_ID}/commands
Eventos publicados:       device/{DEVICE_ID}/events
Telemetría publicada:     device/{DEVICE_ID}/telemetry
Inferencia publicada:     device/{DEVICE_ID}/inference
"""
import asyncio, hashlib, importlib.util, json, logging, os, sys
from pathlib import Path
import aiomqtt, httpx, psutil

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG,
    format="%(asctime)s [edge-agent] %(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

DEVICE_ID = os.environ.get("AURA_DEVICE_ID", "dev-device-001")
MQTT_HOST = os.environ.get("AURA_MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("AURA_MQTT_PORT", "1883"))
WORK_DIR  = Path(os.environ.get("AURA_WORK_DIR", "/tmp/aura"))
TELEMETRY_INTERVAL = int(os.environ.get("AURA_TELEMETRY_INTERVAL", "10"))

WORK_DIR.mkdir(parents=True, exist_ok=True)

_state = {"active_model_id": "", "active_script_id": "", "active_deployment_id": ""}
_script_module = None


async def publish(client: aiomqtt.Client, topic: str, payload: dict):
    await client.publish(topic, json.dumps(payload))

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""): h.update(chunk)
    return h.hexdigest()

async def _download(url: str, dest: Path):
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as http:
        async with http.stream("GET", url) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                async for chunk in r.aiter_bytes(65536): f.write(chunk)

def _load_script(path: Path):
    spec = importlib.util.spec_from_file_location("user_script", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

async def handle_deploy(client: aiomqtt.Client, payload: dict):
    global _script_module, _state
    dep_id     = payload["deployment_id"]
    model_url  = payload["model_url"];  model_sha  = payload["model_sha256"]
    script_url = payload["script_url"]; script_sha = payload["script_sha256"]
    model_id   = payload.get("model_id", "")
    script_id  = payload.get("script_id", "")

    model_path  = WORK_DIR / "model"
    script_path = WORK_DIR / "script.py"
    try:
        logger.info(f"[{dep_id}] Downloading model...")
        await _download(model_url, model_path)
        if _sha256(model_path) != model_sha:
            raise ValueError("Model SHA256 mismatch")

        logger.info(f"[{dep_id}] Downloading script...")
        await _download(script_url, script_path)
        if _sha256(script_path) != script_sha:
            raise ValueError("Script SHA256 mismatch")

        from aura_hw import load_model, unload_model
        unload_model()
        load_model(str(model_path))
        _script_module = _load_script(script_path)

        _state = {"active_model_id": model_id, "active_script_id": script_id,
                  "active_deployment_id": dep_id}
        logger.info(f"[{dep_id}] Deploy OK")
        await publish(client, f"device/{DEVICE_ID}/events",
                      {"event": "deploy_ack", "deployment_id": dep_id})
    except Exception as e:
        logger.error(f"[{dep_id}] Deploy failed: {e}")
        await publish(client, f"device/{DEVICE_ID}/events",
                      {"event": "deploy_failed", "deployment_id": dep_id, "error": str(e)})

async def telemetry_loop(client: aiomqtt.Client):
    while True:
        try:
            mem = psutil.virtual_memory()
            payload = {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "ram_percent": mem.percent,
                "ram_used_mb": round(mem.used / 1024 / 1024, 1),
                **_state,
            }
            await publish(client, f"device/{DEVICE_ID}/telemetry", payload)
        except Exception as e:
            logger.warning(f"Telemetry error: {e}")
        await asyncio.sleep(TELEMETRY_INTERVAL)

async def main():
    logger.info(f"AURA Edge Agent — device_id={DEVICE_ID}")
    while True:
        try:
            async with aiomqtt.Client(hostname=MQTT_HOST, port=MQTT_PORT) as client:
                await client.subscribe(f"device/{DEVICE_ID}/commands")
                logger.info(f"Subscribed to device/{DEVICE_ID}/commands")
                asyncio.create_task(telemetry_loop(client))
                async for msg in client.messages:
                    try:
                        payload = json.loads(msg.payload)
                        cmd = payload.get("command")
                        if cmd == "deploy":
                            asyncio.create_task(handle_deploy(client, payload))
                        else:
                            logger.warning(f"Unknown command: {cmd}")
                    except Exception as e:
                        logger.error(f"Message handling error: {e}")
        except aiomqtt.MqttError as e:
            logger.warning(f"MQTT error: {e} — retrying in 5s")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
