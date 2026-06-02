import logging
from typing import Any
from aura_hw.backends.base import InferenceBackend
logger = logging.getLogger(__name__)

class RPiAICamBackend(InferenceBackend):
    def __init__(self): self._camera = None
    def load(self, model_path: str):
        from picamera2 import Picamera2
        from picamera2.devices.imx500 import IMX500
        self._imx500 = IMX500(model_path)
        self._camera = Picamera2(self._imx500.camera_num)
        self._camera.configure(self._camera.create_preview_configuration(controls={"FrameRate": 10}))
        self._camera.start()
    def infer(self, inputs=None) -> Any:
        return self._imx500.get_outputs(self._camera.capture_metadata())
    def unload(self):
        if self._camera: self._camera.stop(); self._camera = None
    @property
    def hardware_type(self): return "rpi_ai_cam"
