"""
Hailo-8 Asset Preparation Pipeline
==============================================
Prepares the two assets required for Hailo compilation inside Docker:
    1. An ONNX export of your trained YOLO model (NMS stripped, opset 11).
    2. A calibration image directory of 1024 centre-cropped 640×640 JPEGs.

After running this script, transfer the generated .onnx file and calib/
folder into the Hailo Docker shared_with_docker/ volume, then compile with:

    hailomz compile \
        --ckpt shared_with_docker/<model>.onnx \
        --calib-path shared_with_docker/calib \
        --yaml workspace/hailo_model_zoo/hailo_model_zoo/cfg/networks/yolov8n.yaml \
        --classes <NUM_CLASSES> \
        --hw-arch hailo8

Requirements (host machine):
    pip install ultralytics pillow tqdm

Usage examples:
    python hailo_pipeline.py \
        --weights Models/Driver_Drowsiness/runs/weights/best.pt \
        --data_dir Models/Driver_Drowsiness/dataset/images

    python hailo_pipeline.py \
        --weights Models/Driver_Drowsiness/runs/weights/best.pt \
        --data_dir Models/Driver_Drowsiness/dataset/images \
        --calib_dir my_calib_folder \
        --num_calib 512 \
        --image_size 640x640
"""

import argparse
import os
import random
from pathlib import Path

from PIL import Image
from tqdm import tqdm
from ultralytics import YOLO


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare ONNX model and calibration data for Hailo-8/8L compilation.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "--weights", type=str, required=True,
        help="Path to the trained YOLO .pt weights file."
    )
    parser.add_argument(
        "--data_dir", type=str, required=True,
        help="Path to the raw dataset images directory (searched recursively)."
    )
    parser.add_argument(
        "--calib_dir", type=str, default="calib",
        help="Output directory for processed calibration images."
    )
    parser.add_argument(
        "--num_calib", type=int, default=1024,
        help="Number of calibration images to generate."
    )
    parser.add_argument(
        "--image_size", type=str, default="640x640",
        help="Target calibration image size as WxH (e.g. 640x640)."
    )

    return parser.parse_args()


# ---------------------------------------------------------------------------
# Phase 1: ONNX export
# ---------------------------------------------------------------------------

def export_to_onnx(weights_path: str) -> str:
    """
    Export a YOLO .pt model to ONNX with Hailo-compatible settings:
      - nms=False  : strips NMS so Hailo can inject its own hardware-accelerated NMS
      - opset=11   : guarantees compatibility with the Hailo Dataflow Compiler
      - batch=1    : locks dimensions for single-frame real-time edge streaming
    """
    print("\n" + "=" * 60)
    print("  PHASE 1: Exporting model to ONNX")
    print("=" * 60)

    if not os.path.exists(weights_path):
        raise FileNotFoundError(f"Weights file not found: '{weights_path}'")

    print(f"  Loading YOLO model from '{weights_path}'...")
    model = YOLO(weights_path)

    print("  Exporting (nms=False, opset=11, batch=1)...")
    onnx_path = model.export(format="onnx", batch=1, nms=False, opset=11)

    print(f"  ONNX model saved to: {onnx_path}")
    return onnx_path


# ---------------------------------------------------------------------------
# Phase 2: Calibration data generation
# ---------------------------------------------------------------------------

def generate_calibration_data(
    data_dir: str,
    calib_dir: str,
    num_images: int,
    size: tuple,
) -> str:
    """
    Select `num_images` images from `data_dir`, apply centre-crop resize
    to `size`, and save as JPEG into `calib_dir`.

    Centre-crop logic:
      1. Scale the image so its shortest side fully covers `size`.
      2. Crop the centre `size` region — avoids distortion that degrades INT8 accuracy.
    """
    print("\n" + "=" * 60)
    print("  PHASE 2: Generating calibration dataset")
    print("=" * 60)

    os.makedirs(calib_dir, exist_ok=True)

    # Supported extensions
    extensions = {".jpg", ".jpeg", ".png"}

    print(f"  Searching for images in '{data_dir}'...")
    all_images = [
        os.path.join(root, f)
        for root, _, files in os.walk(data_dir)
        for f in files
        if Path(f).suffix.lower() in extensions
    ]

    if not all_images:
        raise ValueError(
            f"No images found in '{data_dir}'.\n"
            "Supported formats: .jpg, .jpeg, .png"
        )

    random.shuffle(all_images)
    selected = all_images[:num_images]
    print(f"  Selected {len(selected)} images (requested: {num_images})")

    valid_count = 0
    skipped     = 0

    for img_path in tqdm(selected, desc="  Processing"):
        try:
            # Verify image integrity before processing
            with Image.open(img_path) as img:
                img.verify()

            with Image.open(img_path) as img:
                img = img.convert("RGB")

                # Scale so shortest side covers target
                ratio = max(size[0] / img.width, size[1] / img.height)
                new_w = int(img.width  * ratio)
                new_h = int(img.height * ratio)
                img   = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                # Centre crop
                left = (img.width  - size[0]) // 2
                top  = (img.height - size[1]) // 2
                img  = img.crop((left, top, left + size[0], top + size[1]))

                out_path = os.path.join(calib_dir, f"calib_{valid_count}.jpg")
                img.save(out_path, format="JPEG", quality=95)
                valid_count += 1

        except Exception:
            skipped += 1
            continue

    print(f"  Generated {valid_count} calibration images -> '{calib_dir}/'")
    if skipped:
        print(f"  Skipped {skipped} corrupted or unreadable files.")

    return calib_dir


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_arguments()

    # Parse image size
    img_w, img_h = map(int, args.image_size.split("x"))
    image_size = (img_w, img_h)

    # Run both phases
    onnx_file   = export_to_onnx(args.weights)
    calib_folder = generate_calibration_data(
        data_dir   = args.data_dir,
        calib_dir  = args.calib_dir,
        num_images = args.num_calib,
        size       = image_size,
    )

    print("\n" + "=" * 60)
    print("  PREPARATION COMPLETE")
    print("=" * 60)
    print(f"  ONNX model  : {onnx_file}")
    print(f"  Calib images: {calib_folder}/")
    print("\n  Next step — move both into your Hailo Docker shared volume and run:")
    print("    hailomz compile \\")
    print(f"        --ckpt shared_with_docker/{os.path.basename(onnx_file)} \\")
    print(f"        --calib-path shared_with_docker/{os.path.basename(calib_folder)} \\")
    print("        --yaml workspace/hailo_model_zoo/.../yolov8n.yaml \\")
    print("        --classes <NUM_CLASSES> \\")
    print("        --hw-arch hailo8")


if __name__ == "__main__":
    main()
