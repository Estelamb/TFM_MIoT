import logging
from aura_hw.backends.base import InferenceBackend
logger = logging.getLogger(__name__)

class JetsonTRTBackend(InferenceBackend):
    def load(self, model_path: str): logger.warning("JetsonTRT: stub pendiente")
    def infer(self, inputs) -> dict: logger.warning("JetsonTRT: output vacío (stub)"); return {}
    def unload(self): pass
    @property
    def hardware_type(self): return "jetson_orin_nano"
