import logging
from typing import Any
import numpy as np
from aura_hw.backends.base import InferenceBackend
logger = logging.getLogger(__name__)

class HailoBackend(InferenceBackend):
    def __init__(self, hw_type="hailo8"): self._hw_type = hw_type; self._target = None
    def load(self, model_path: str):
        from hailo_platform import HEF, VDevice, HailoSchedulingAlgorithm, InputVStreamParams, OutputVStreamParams, FormatType
        params = VDevice.create_params()
        params.scheduling_algorithm = HailoSchedulingAlgorithm.ROUND_ROBIN
        self._target = VDevice(params=params)
        self._hef = HEF(model_path)
        self._ng = self._target.configure(self._hef)[0]
        self._inp = InputVStreamParams.make(self._ng, format_type=FormatType.FLOAT32)
        self._out = OutputVStreamParams.make(self._ng, format_type=FormatType.FLOAT32)
        logger.info(f"Hailo model loaded: {model_path}")
    def infer(self, inputs) -> Any:
        from hailo_platform import InferVStreams
        with InferVStreams(self._ng, self._inp, self._out) as p:
            with self._ng.activate():
                data = {list(self._inp.keys())[0]: inputs} if isinstance(inputs, np.ndarray) else inputs
                p.send(data); return p.recv()
    def unload(self):
        if self._target: self._target.release(); self._target = None
    @property
    def hardware_type(self): return self._hw_type
