import os
from daemon.shared import logger, HARDWARE_TYPE


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


hailo_manager = HailoManager()
