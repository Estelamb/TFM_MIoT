"""
AURA Edge Script — Plantilla YOLOv8
====================================
Implementa pre_inference() y post_inference().
NO modifiques la firma de las funciones ni la función run().
"""
from __future__ import annotations
from typing import Any
import numpy as np
from aura_hw import execute_inference

INPUT_WIDTH  = 640
INPUT_HEIGHT = 640
CONF_THRESHOLD = 0.5
CLASSES = ["person", "car", "dog"]  # ajusta a tus labels

def pre_inference(raw_input: Any) -> np.ndarray:
    import cv2
    img = cv2.resize(raw_input, (INPUT_WIDTH, INPUT_HEIGHT))
    img = img.astype(np.float32) / 255.0
    img = np.transpose(img, (2, 0, 1))   # HWC → CHW
    return np.expand_dims(img, axis=0)   # → NCHW

def post_inference(raw_output: Any) -> list[dict]:
    detections = []
    outputs = list(raw_output.values())[0] if isinstance(raw_output, dict) else raw_output
    if outputs is None or len(outputs) == 0:
        return detections
    for box in outputs[0].T:
        scores = box[4:]
        class_id = int(np.argmax(scores))
        confidence = float(scores[class_id])
        if confidence < CONF_THRESHOLD:
            continue
        cx, cy, w, h = box[:4]
        detections.append({
            "class": CLASSES[class_id] if class_id < len(CLASSES) else str(class_id),
            "confidence": round(confidence, 3),
            "bbox": [float(cx), float(cy), float(w), float(h)],
        })
    return detections

# ── NO modificar ─────────────────────────────────────────────────────────────
def run(raw_input: Any) -> list[dict]:
    return post_inference(execute_inference(pre_inference(raw_input)))
