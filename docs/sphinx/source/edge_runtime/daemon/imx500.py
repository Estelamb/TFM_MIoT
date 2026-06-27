import os
from daemon.shared import logger, HARDWARE_TYPE
from daemon.camera import CameraManager, camera_manager


class IMX500Manager:
    """Manages dynamic loading and inference execution of IMX500 models on the host."""
    def __init__(self, camera_mgr: CameraManager) -> None:
        self.camera_mgr = camera_mgr
        self.model_path = None

    def load(self, rpk_bytes: bytes) -> dict:
        if HARDWARE_TYPE != "rpi_ai_cam":
            return {"status": "error", "error": f"RPi AI Cam is not enabled (configured hardware type: {HARDWARE_TYPE})"}
        try:
            self.unload()
            
            # Try to import IMX500
            HAS_IMX500 = False
            try:
                from picamera2.devices import IMX500
                HAS_IMX500 = True
            except ImportError:
                logger.warning("picamera2.devices.IMX500 not available on host. Using simulated IMX500.")
                
            import tempfile
            fd, path = tempfile.mkstemp(suffix=".rpk")
            with os.fdopen(fd, "wb") as tmp:
                tmp.write(rpk_bytes)
            self.model_path = path
            
            logger.info(f"Loading IMX500 RPK model from {path}...")
            
            # Stop the camera manager background thread before changing the device
            self.camera_mgr.stop()
            
            if HAS_IMX500:
                self.camera_mgr.imx500 = IMX500(self.model_path)
                h, w = self.camera_mgr.imx500.get_input_size()
            else:
                # Simulated IMX500 instance
                class SimulatedIMX500:
                    def __init__(self):
                        self.camera_num = 0
                    def get_input_size(self):
                        return (640, 640)
                    def show_network_fw_progress_bar(self):
                        pass
                self.camera_mgr.imx500 = SimulatedIMX500()
                h, w = 640, 640
                
            # Restart the camera manager with the IMX500 loaded
            self.camera_mgr.start()
            
            logger.info(f"IMX500 model loaded successfully. Input shape: {w}x{h}")
            return {"status": "success", "input_shape": [h, w, 3]}
        except Exception as e:
            logger.error(f"Error loading IMX500 model: {e}")
            self.unload()
            return {"status": "error", "error": str(e)}

    def infer(self) -> dict:
        if self.camera_mgr.imx500 is None:
            return {"status": "error", "error": "No model loaded"}
        
        with self.camera_mgr.lock:
            outputs = self.camera_mgr.latest_outputs
            
        if outputs is None:
            return {"status": "success", "detections": []}
            
        return {"status": "success", "detections": outputs}

    def unload(self) -> None:
        if self.camera_mgr.imx500 is not None:
            self.camera_mgr.stop()
            self.camera_mgr.imx500 = None
            # Restart camera as a standard camera (without model loaded)
            self.camera_mgr.start()
            
        if self.model_path and os.path.exists(self.model_path):
            try:
                os.remove(self.model_path)
            except Exception:
                pass
            self.model_path = None


imx500_manager = IMX500Manager(camera_manager)
