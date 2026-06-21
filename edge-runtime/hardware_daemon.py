#!/usr/bin/env python3
"""
AURA Hardware Daemon
====================
Exposes Raspberry Pi Camera Module 3 and Hailo-8/8L hardware accelerators
over a lightweight local HTTP API.
Allows containerized edge agents to interact with native hardware without
complex device mounts or privileged Docker flags.

API Endpoints:
* GET /capture - Returns the latest captured frame as 'image/jpeg' bytes.
* GET /status  - Returns JSON status of the daemon (physical vs simulated).
* POST /load   - Accepts raw HEF bytes and initializes Hailo context.
* POST /infer  - Runs inference on the loaded Hailo model using raw RGB888 bytes.
* POST /unload - Releases the Hailo context and cleans up temporary HEFs.
"""
import io
import json
import logging
import os
import sys
import time
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [AURA-Daemon] %(levelname)s — %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger("hardware_daemon")

# Try to import Pillow (PIL) for fallback simulation
try:
    from PIL import Image, ImageDraw
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

# Fallback minimal 1x1 black JPEG image bytes in case Pillow is missing
MINIMAL_JPEG = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00\x37\xff\xd9'


def load_config() -> tuple[str, bool]:
    """Resolves the hardware_type and whether the camera is enabled.
    Looks in: env vars > config/device_config.yaml and config/components_config.yaml > defaults.
    """
    import yaml
    
    # 1. Resolve hardware_type
    hw_type = os.environ.get("AURA_HARDWARE_TYPE")
    if not hw_type:
        config_dirs = [
            Path(__file__).parent / "config",
            Path("/app/config"),
            Path("./config"),
            Path(".")
        ]
        for cdir in config_dirs:
            device_path = cdir / "device_config.yaml"
            if device_path.exists():
                try:
                    with open(device_path, "r", encoding="utf-8") as f:
                        cfg = yaml.safe_load(f) or {}
                        hw_type = cfg.get("hardware_type")
                        if hw_type:
                            break
                except Exception:
                    pass
    
    if not hw_type or hw_type.lower() == "auto":
        hw_type = "rpi"  # Default fallback, no physical auto-probing
    else:
        hw_type = hw_type.lower()

    # 2. Resolve camera enabled state
    cam_enabled_env = os.environ.get("AURA_CAMERA_ENABLED")
    if cam_enabled_env is not None:
        camera_enabled = cam_enabled_env.lower() in ("true", "1", "yes")
    else:
        camera_enabled = False
        config_dirs = [
            Path(__file__).parent / "config",
            Path("/app/config"),
            Path("./config"),
            Path(".")
        ]
        for cdir in config_dirs:
            comp_path = cdir / "components_config.yaml"
            if comp_path.exists():
                try:
                    with open(comp_path, "r", encoding="utf-8") as f:
                        comp_cfg = yaml.safe_load(f) or {}
                        components = comp_cfg.get("components", [])
                        for comp in components:
                            if comp.get("type") == "camera":
                                if comp.get("enabled", True):
                                    camera_enabled = True
                                    break
                except Exception:
                    pass
                break

    return hw_type, camera_enabled


HARDWARE_TYPE, CAMERA_ENABLED = load_config()
logger.info(f"Loaded config: hardware_type={HARDWARE_TYPE}, camera_enabled={CAMERA_ENABLED}")


class CameraManager:
    """Manages camera lifecycle and captures frame to memory."""
    def __init__(self) -> None:
        self.picam2 = None
        self.is_active = False

    def start(self) -> None:
        if CAMERA_ENABLED:
            logger.info("Initializing native Picamera2 (Camera Module 3)...")
            try:
                from picamera2 import Picamera2
                self.picam2 = Picamera2()
                config = self.picam2.create_preview_configuration(
                    main={"size": (640, 480), "format": "RGB888"}
                )
                self.picam2.configure(config)
                self.picam2.start()
                self.is_active = True
                logger.info("Picamera2 started successfully.")
            except Exception as e:
                logger.error(f"Error starting Picamera2: {e}")
                self.picam2 = None
                self.is_active = False
        else:
            logger.info("Picamera2 is disabled via configuration. Simulated fallback will be used.")
            self.is_active = True

    def capture_raw(self) -> bytes:
        if not self.is_active:
            return bytes(640 * 480 * 3)
            
        if self.picam2:
            try:
                # Capture frame natively as a numpy array
                frame = self.picam2.capture_array()
                return frame.tobytes()
            except Exception as e:
                logger.error(f"Error capturing physical frame: {e}")
                return bytes(640 * 480 * 3)
        else:
            # Simulated frame fallback
            if HAS_PILLOW:
                try:
                    # Create dark background image
                    img = Image.new("RGB", (640, 480), color=(30, 32, 36))
                    draw = ImageDraw.Draw(img)
                    
                    # Animated moving bars to show active loop
                    t = int(time.time() * 20) % 480
                    draw.rectangle([0, t, 640, min(t+30, 480)], fill=(235, 69, 75))
                    t2 = int(time.time() * 30) % 640
                    draw.rectangle([t2, 0, min(t2+30, 640), 480], fill=(114, 137, 218))
                    
                    # Convert Pillow Image to raw RGB bytes
                    return img.tobytes()
                except Exception as e:
                    logger.error(f"Error generating Pillow mock frame: {e}")
                    return bytes(640 * 480 * 3)
            else:
                return bytes(640 * 480 * 3)

    def stop(self) -> None:
        if self.picam2:
            try:
                self.picam2.stop()
                logger.info("Picamera2 stopped successfully.")
            except Exception as e:
                logger.error(f"Error stopping Picamera2: {e}")
            self.picam2 = None
        self.is_active = False


class HailoManager:
    """Manages dynamic loading and inference execution of Hailo HEF models on the host."""
    def __init__(self) -> None:
        self.hailo = None
        self.model_path = None

    def load(self, hef_bytes: bytes) -> dict:
        if HARDWARE_TYPE not in ("hailo8", "hailo8l"):
            return {"status": "error", "error": f"Hailo is not enabled (configured hardware type: {HARDWARE_TYPE})"}
        try:
            self.unload()
            
            # Dynamic import of Hailo on the host
            try:
                from picamera2.devices import Hailo
            except ImportError:
                return {"status": "error", "error": "Hailo runtime library (picamera2.devices.Hailo) not available on host"}
                
            # Workaround for picamera2 bug where static TARGET is not reset to None on release
            try:
                Hailo.TARGET = None
                Hailo.TARGET_REF_COUNT = 0
            except Exception as e:
                logger.warning(f"Failed to reset Hailo target variables: {e}")
                
            import tempfile
            fd, path = tempfile.mkstemp(suffix=".hef")
            with os.fdopen(fd, "wb") as tmp:
                tmp.write(hef_bytes)
            self.model_path = path
            
            logger.info(f"Loading Hailo HEF model from {path}...")
            self.hailo = Hailo(self.model_path)
            self.hailo.__enter__()
            
            h, w, c = self.hailo.get_input_shape()
            logger.info(f"Hailo HEF model loaded successfully. Input shape: {w}x{h}")
            return {"status": "success", "input_shape": [h, w, c]}
        except Exception as e:
            logger.error(f"Error loading Hailo model: {e}")
            self.unload()
            return {"status": "error", "error": str(e)}

    def infer(self, img_bytes: bytes, w: int, h: int) -> dict:
        if not self.hailo:
            return {"status": "error", "error": "No model loaded"}
        try:
            import numpy as np
            import cv2
            img = np.frombuffer(img_bytes, dtype=np.uint8).reshape((h, w, 3)).copy()
            
            model_h, model_w, _ = self.hailo.get_input_shape()
            if img.shape[0] != model_h or img.shape[1] != model_w:
                img = cv2.resize(img, (model_w, model_h))
                
            detections = self.hailo.run(img)
            return {"status": "success", "detections": detections}
        except Exception as e:
            logger.error(f"Error during Hailo inference: {e}")
            return {"status": "error", "error": str(e)}

    def unload(self) -> None:
        if self.hailo:
            try:
                self.hailo.__exit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error exiting Hailo context: {e}")
            self.hailo = None
            
        try:
            from picamera2.devices import Hailo
            Hailo.TARGET = None
            Hailo.TARGET_REF_COUNT = 0
        except Exception:
            pass
            
        if self.model_path and os.path.exists(self.model_path):
            try:
                os.remove(self.model_path)
            except Exception:
                pass
            self.model_path = None


camera_manager = CameraManager()
hailo_manager = HailoManager()


def _make_json_serializable(val: Any) -> Any:
    import numpy as np
    if isinstance(val, np.ndarray):
        return val.tolist()
    if isinstance(val, dict):
        return {k: _make_json_serializable(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [_make_json_serializable(v) for v in val]
    if isinstance(val, (np.integer, np.floating)):
        return val.item()
    return val


class HardwareHTTPHandler(BaseHTTPRequestHandler):
    """Lite HTTP handler resolving requests."""
    def log_message(self, format, *args):
        # Silence default access logging to keep console clean during rapid capture requests
        pass

    def do_GET(self) -> None:
        if self.path == "/capture":
            raw_data = camera_manager.capture_raw()
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(raw_data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(raw_data)
        elif self.path == "/status":
            try:
                from picamera2 import Picamera2
                picam_avail = True
            except ImportError:
                picam_avail = False

            try:
                from picamera2.devices import Hailo
                hailo_avail = True
            except ImportError:
                hailo_avail = False
            
            status = {
                "status": "online",
                "hardware_type": HARDWARE_TYPE,
                "camera_type": "physical" if (picam_avail and CAMERA_ENABLED) else "simulated",
                "picamera_available": picam_avail,
                "camera_enabled": CAMERA_ENABLED,
                "hailo_available": hailo_avail,
                "pillow_available": HAS_PILLOW
            }
            body = json.dumps(status).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        
        # Read content length
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b""
        
        if path == "/load":
            res = hailo_manager.load(post_data)
            body = json.dumps(res).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
            
        elif path == "/infer":
            params = urllib.parse.parse_qs(parsed_url.query)
            w = int(params.get('w', [640])[0])
            h = int(params.get('h', [480])[0])
            
            res = hailo_manager.infer(post_data, w, h)
            res = _make_json_serializable(res)
            body = json.dumps(res).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
            
        elif path == "/unload":
            hailo_manager.unload()
            body = json.dumps({"status": "success"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
            
        else:
            self.send_response(404)
            self.end_headers()


def main() -> None:
    import signal
    
    port = 8008
    camera_manager.start()
    
    server = HTTPServer(("0.0.0.0", port), HardwareHTTPHandler)
    logger.info(f"AURA Hardware Daemon listening on http://0.0.0.0:{port}")
    
    def shutdown_handler(signum, frame) -> None:
        logger.info("Shutdown signal received. Stopping daemon...")
        camera_manager.stop()
        hailo_manager.unload()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        camera_manager.stop()
        hailo_manager.unload()


if __name__ == "__main__":
    main()


