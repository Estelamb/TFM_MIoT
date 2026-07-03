# How to Create a Custom Inference Script

In the AURA Platform, an **Inference Script** is a user-defined Python module (`.py`) uploaded via the web console. The script defines how to preprocess raw inputs, run the neural network, and postprocess the results on the edge device.

The Edge Runtime dynamically loads this script and invokes its entrypoint for every incoming camera frame or sensory input.

---

## 1. The Script structure

Every inference script must implement the following components:

1. **`pre_inference(raw_input)`**: Processes the raw system input (e.g. OpenCV image frame, NumPy array, or JSON string) and transforms it into the format expected by the model.
2. **`post_inference(raw_output)`**: Parses the raw model outputs (typically a collection of PyTorch or ONNX tensors) into a structured JSON serializable list of dictionaries.
3. **`run(raw_input)`**: The main execution entrypoint. This function is invoked periodically by the AURA agent loop.
4. **`execute_inference()` function**: Imported from the special virtual library `aura_hw`, this function automatically executes the loaded model on the active NPU/CPU accelerator backend.

---

## 2. Example: Object Detection Script

Below is a complete, production-ready template for a YOLOv8 object detection script:

```python
import numpy as np
from PIL import Image
import io

# Import the AURA hardware execution helper
from aura_hw import execute_inference

def pre_inference(raw_input):
    """Preprocess the raw input bytes into a normalized tensor.
    
    Args:
        raw_input: Raw image bytes from the camera/sensor source.
    """
    # 1. Load image from bytes
    image = Image.open(io.BytesIO(raw_input)).convert("RGB")
    
    # 2. Resize to YOLO default 640x640
    image = image.resize((640, 640))
    
    # 3. Convert to float32 NumPy array and normalize to [0.0, 1.0]
    img_data = np.array(image).astype(np.float32) / 255.0
    
    # 4. Transpose from HWC to BCHW (1, 3, 640, 640)
    img_data = np.transpose(img_data, (2, 0, 1))
    img_data = np.expand_dims(img_data, axis=0)
    
    return img_data

def post_inference(raw_output):
    """Postprocess raw output tensors to retrieve bounding boxes.
    
    Args:
        raw_output: Outputs returned by the accelerator model backend.
    """
    # Exclude dummy/empty inputs
    if raw_output is None or len(raw_output) == 0:
        return []
        
    predictions = raw_output[0]  # Shape: (1, 84, 8400) for YOLOv8
    
    results = []
    # Parse bounding boxes, confidence score, and class IDs
    # (Simplistic dummy parse; replace with actual NMS logic if running custom raw models)
    for box in predictions[0][:5]:  # Process the top 5 boxes
        x_center, y_center, width, height, confidence = box[:5]
        if confidence > 0.5:
            results.append({
                "class": "object",
                "confidence": float(confidence),
                "bbox": [
                    float(x_center - width / 2),
                    float(y_center - height / 2),
                    float(width),
                    float(height)
                ]
            })
            
    return results

def run(raw_input):
    """Main entrypoint function called by the AURA agent runtime.
    
    Args:
        raw_input: The raw data payload.
    """
    # 1. Preprocess raw input
    tensor = pre_inference(raw_input)
    
    # 2. Execute inference on target hardware accelerator
    raw_results = execute_inference(tensor)
    
    # 3. Postprocess outputs and return structured JSON objects
    return post_inference(raw_results)
```

---

## 3. Uploading and deploying scripts

Once your script is ready:
1. Save it locally as a standard Python file (e.g. `detect_people.py`).
2. Open the **AURA Web Management Console**.
3. Navigate to **Scripts** and click **Upload Script**.
4. Upload your file, give it a name and version (e.g. `v1.0.0`), and save.
5. You can now select this script during the **New Deployment** creation flow alongside your target compiled model. The platform will automatically bundle and deploy it to the selected device.
