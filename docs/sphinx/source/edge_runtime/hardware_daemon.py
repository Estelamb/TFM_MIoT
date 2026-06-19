#!/usr/bin/env python3
"""
AURA Hardware Daemon
====================
Exposes Raspberry Pi Camera Module 3 over a lightweight local HTTP API.
Allows containerized edge agents to interact with native hardware without
complex device mounts or privileged Docker flags.

API Endpoints:
* GET /capture - Returns the latest captured frame as 'image/jpeg' bytes.
* GET /status  - Returns JSON status of the daemon (physical vs simulated).
"""
import io
import json
import logging
import os
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [AURA-Daemon] %(levelname)s — %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger("hardware_daemon")

# Try to import picamera2
try:
    from picamera2 import Picamera2
    HAS_PICAMERA = True
except ImportError:
    HAS_PICAMERA = False

# Try to import Pillow (PIL) for fallback simulation
try:
    from PIL import Image, ImageDraw
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

# Fallback minimal 1x1 black JPEG image bytes in case Pillow is missing
MINIMAL_JPEG = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00\x37\xff\xd9'


class CameraManager:
    """Manages camera lifecycle and captures frame to memory."""
    def __init__(self) -> None:
        self.picam2 = None
        self.is_active = False

    def start(self) -> None:
        if HAS_PICAMERA:
            logger.info("Initializing native Picamera2 (Camera Module 3)...")
            try:
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
            logger.warning("Picamera2 not found. Exposing Simulated/Mock Camera instead.")
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


camera_manager = CameraManager()


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
            status = {
                "status": "online",
                "camera_type": "physical" if HAS_PICAMERA else "simulated",
                "picamera_available": HAS_PICAMERA,
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


def main() -> None:
    import signal
    
    port = 8008
    camera_manager.start()
    
    server = HTTPServer(("0.0.0.0", port), HardwareHTTPHandler)
    logger.info(f"AURA Hardware Daemon listening on http://0.0.0.0:{port}")
    
    def shutdown_handler(signum, frame) -> None:
        logger.info("Shutdown signal received. Stopping daemon...")
        camera_manager.stop()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        camera_manager.stop()


if __name__ == "__main__":
    main()
