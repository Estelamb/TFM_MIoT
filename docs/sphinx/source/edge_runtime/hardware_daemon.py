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
import threading
import numpy as np
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

# Import config, utilities, and manager singletons from daemon package
from daemon.shared import logger, HARDWARE_TYPE, CAMERA_ENABLED, HAS_PILLOW, _make_json_serializable
from daemon import camera_manager, hailo_manager, imx500_manager


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

            try:
                from picamera2.devices import IMX500
                imx500_avail = True
            except ImportError:
                imx500_avail = False
            
            status = {
                "status": "online",
                "hardware_type": HARDWARE_TYPE,
                "camera_type": "physical" if (picam_avail and CAMERA_ENABLED) else "simulated",
                "picamera_available": picam_avail,
                "camera_enabled": CAMERA_ENABLED,
                "hailo_available": hailo_avail,
                "imx500_available": imx500_avail,
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
            if HARDWARE_TYPE == "rpi_ai_cam":
                res = imx500_manager.load(post_data)
            else:
                res = hailo_manager.load(post_data)
            body = json.dumps(res).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
            
        elif path == "/infer":
            if HARDWARE_TYPE == "rpi_ai_cam":
                res = imx500_manager.infer()
            else:
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
            if HARDWARE_TYPE == "rpi_ai_cam":
                imx500_manager.unload()
            else:
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
        imx500_manager.unload()
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


