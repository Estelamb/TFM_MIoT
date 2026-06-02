import logging
from typing import Any
import numpy as np
from aura_hw.backends.base import InferenceBackend
logger = logging.getLogger(__name__)

class RPiTFLiteBackend(InferenceBackend):
    def __init__(self): self._interp = None
    def load(self, model_path: str):
        try:
            from tflite_runtime.interpreter import Interpreter
        except ImportError:
            import tensorflow as tf; Interpreter = tf.lite.Interpreter
        self._interp = Interpreter(model_path=model_path)
        self._interp.allocate_tensors()
        self._inp = self._interp.get_input_details()
        self._out = self._interp.get_output_details()
    def infer(self, inputs) -> Any:
        if isinstance(inputs, np.ndarray): self._interp.set_tensor(self._inp[0]['index'], inputs)
        else:
            for d in self._inp: self._interp.set_tensor(d['index'], inputs[d['name']])
        self._interp.invoke()
        return {d['name']: self._interp.get_tensor(d['index']) for d in self._out}
    def unload(self): self._interp = None
    @property
    def hardware_type(self): return "rpi"
