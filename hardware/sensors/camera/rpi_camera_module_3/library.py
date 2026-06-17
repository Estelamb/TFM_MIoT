"""
AURA Sensor Library: RPi Camera Module 3
========================================
"""
import logging

logger = logging.getLogger(__name__)

LABEL = "RPi Camera Module 3"

class RPiCameraLibrary:
    def __init__(self, camera_id: int = 0, resolution: tuple[int, int] = (640, 480), fps: int = 10, **kwargs):
        self.camera_id = camera_id
        # Support either string resolution "[640, 480]" or list/tuple
        if isinstance(resolution, str):
            try:
                import json
                self.resolution = tuple(json.loads(resolution))
            except Exception:
                self.resolution = (640, 480)
        elif isinstance(resolution, (list, tuple)):
            self.resolution = tuple(resolution)
        else:
            self.resolution = (640, 480)
            
        self.fps = int(fps)
        self.picam2 = None

    def initialize(self) -> bool:
        """Initialize and configure the Picamera2 camera."""
        logger.info("Initializing Picamera2 (RPi Camera Module 3)...")
        try:
            from picamera2 import Picamera2
            self.picam2 = Picamera2()
            
            # Configure to output raw RGB frames at configured resolution
            config = self.picam2.create_preview_configuration(
                main={"size": self.resolution, "format": "RGB888"}
            )
            self.picam2.configure(config)
            self.picam2.start()
            logger.info("Picamera2 started successfully.")
            return True
        except ImportError:
            logger.error("picamera2 module not found. Camera module cannot run natively on this system.")
            return False
        except Exception as e:
            logger.error(f"Error starting RPi Camera Module 3: {e}")
            return False

    def read_value(self):
        """Capture an RGB image frame from the camera."""
        if self.picam2 is None:
            raise RuntimeError("RPi Camera Module 3 is not initialized. Call initialize() first.")
        try:
            # Capture frame natively as an RGB numpy array
            return self.picam2.capture_array()
        except Exception as e:
            logger.error(f"Error capturing frame from RPi Camera Module 3: {e}")
            raise

    def capture_frame(self):
        return self.read_value()

    def close(self) -> None:
        """Stop and release camera resources."""
        if self.picam2 is not None:
            try:
                self.picam2.stop()
                logger.info("Picamera2 stopped successfully.")
            except Exception as e:
                logger.warning(f"Error stopping Picamera2: {e}")
            finally:
                self.picam2 = None
