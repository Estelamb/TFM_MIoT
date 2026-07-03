import time
import threading
import numpy as np
from daemon.shared import logger, HARDWARE_TYPE, CAMERA_ENABLED, HAS_PILLOW

# Try to import Pillow (PIL) for fallback simulation
if HAS_PILLOW:
    from PIL import Image, ImageDraw


class CameraManager:
    """Manages camera lifecycle and captures frame to memory."""
    def __init__(self) -> None:
        self.picam2 = None
        self.imx500 = None
        self.is_active = False
        self.latest_frame = None
        self.latest_outputs = None
        self.lock = threading.Lock()
        self.thread = None
        self.stop_event = threading.Event()

    def start(self) -> None:
        self.stop() # Ensure clean state
        self.stop_event.clear()
        self.latest_frame = None
        self.latest_outputs = None
        
        if CAMERA_ENABLED:
            logger.info("Initializing native Picamera2 (Camera Module 3)...")
            try:
                from picamera2 import Picamera2
                if self.imx500 is not None:
                    self.picam2 = Picamera2(self.imx500.camera_num)
                    config = self.picam2.create_preview_configuration(
                        main={"size": (640, 480), "format": "RGB888"},
                        buffer_count=12
                    )
                    if hasattr(self.imx500, "show_network_fw_progress_bar"):
                        self.imx500.show_network_fw_progress_bar()
                else:
                    self.picam2 = Picamera2()
                    config = self.picam2.create_preview_configuration(
                        main={"size": (640, 480), "format": "RGB888"}
                    )
                self.picam2.configure(config)
                self.picam2.start(show_preview=False)
                self.is_active = True
                logger.info("Picamera2 started successfully.")
            except Exception as e:
                logger.error(f"Error starting Picamera2: {e}")
                self.picam2 = None
                self.is_active = False
        else:
            logger.info("Picamera2 is disabled via configuration. Simulated fallback will be used.")
            self.is_active = True

        # Launch background capture loop
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

    def _capture_loop(self) -> None:
        logger.info("Camera capture loop started.")
        while not self.stop_event.is_set():
            if self.picam2:
                try:
                    if self.imx500:
                        # Native RPi AI Camera request capture
                        request = self.picam2.capture_request()
                        metadata = request.get_metadata()
                        frame = request.make_array("main")
                        # Extract raw tensors
                        outputs = self.imx500.get_outputs(metadata)
                        # Convert frame to RGB bytes
                        frame_bytes = frame.tobytes()
                        with self.lock:
                            self.latest_frame = frame_bytes
                            self.latest_outputs = outputs
                        request.release()
                    else:
                        # Native normal capture
                        frame = self.picam2.capture_array()
                        frame_bytes = frame.tobytes()
                        with self.lock:
                            self.latest_frame = frame_bytes
                            self.latest_outputs = None
                except Exception as e:
                    logger.error(f"Error in physical camera capture loop: {e}")
                    time.sleep(0.1)
            else:
                # Simulated capture loop
                outputs = None
                if HARDWARE_TYPE == "rpi_ai_cam" and self.imx500 is not None:
                    boxes = np.array([[100.0, 100.0, 300.0, 300.0]], dtype=np.float32)
                    # class 1 (so raw_class = 1 / 256.0 = 0.00390625)
                    classes = np.array([1.0 / 256.0], dtype=np.float32)
                    scores = np.array([0.85], dtype=np.float32)
                    count = np.array([1], dtype=np.float32)
                    outputs = [boxes, classes, scores, count]

                if HAS_PILLOW:
                    try:
                        # Create simulated image
                        img = Image.new("RGB", (640, 480), color=(30, 32, 36))
                        draw = ImageDraw.Draw(img)
                        t = int(time.time() * 20) % 480
                        draw.rectangle([0, t, 640, min(t+30, 480)], fill=(235, 69, 75))
                        t2 = int(time.time() * 30) % 640
                        draw.rectangle([t2, 0, min(t2+30, 640), 480], fill=(114, 137, 218))
                        
                        frame_bytes = img.tobytes()
                        with self.lock:
                            self.latest_frame = frame_bytes
                            self.latest_outputs = outputs
                    except Exception as e:
                        logger.error(f"Error in simulated capture loop: {e}")
                else:
                    with self.lock:
                        self.latest_frame = bytes(640 * 480 * 3)
                        self.latest_outputs = outputs
                time.sleep(0.1)

    def capture_raw(self) -> bytes:
        with self.lock:
            frame = self.latest_frame
        if frame is not None:
            return frame
        return bytes(640 * 480 * 3)

    def stop(self) -> None:
        self.stop_event.set()
        if self.picam2:
            try:
                self.picam2.stop()
                logger.info("Picamera2 stopped successfully.")
            except Exception as e:
                logger.error(f"Error stopping Picamera2: {e}")
        
        if self.thread is not None:
            self.thread.join(timeout=2.0)
            self.thread = None
            
        if self.picam2:
            try:
                self.picam2.close()
                logger.info("Picamera2 closed successfully.")
            except Exception as e:
                logger.error(f"Error closing Picamera2: {e}")
            self.picam2 = None
        self.is_active = False


camera_manager = CameraManager()
