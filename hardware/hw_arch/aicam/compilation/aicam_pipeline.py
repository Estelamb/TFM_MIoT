"""
Sony IMX500 (AI Camera) Compilation Pipeline
=============================================
Exports a trained YOLO .pt model to the IMX500 format (packerOut.zip)
suitable for deployment on a Raspberry Pi AI Camera.

Pipeline steps:
    1. Create a temporary calibration YAML pointing to a subset of training images.
    2. Load the YOLO model and run model.export(format="imx").
    3. Verify that packerOut.zip was produced.
    4. Clean up temporary files.

Requirements (host machine):
    pip install model-compression-toolkit imx500-converter[pt]
    pip install torch==2.6.0 torchvision==0.21.0 onnx==1.17.0

Usage examples:
    python aicam_pipeline.py \
        --weights Models/Driver_Drowsiness/runs/weights/best.pt \
        --dataset_dir Models/Driver_Drowsiness/dataset

    python aicam_pipeline.py \
        --weights Models/Driver_Drowsiness/runs/weights/best.pt \
        --dataset_dir Models/Driver_Drowsiness/dataset \
        --calib_samples 300
"""

import argparse
import os
import shutil
from glob import glob
from ultralytics import YOLO


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a YOLO model to Sony IMX500 format (packerOut.zip).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "--weights", type=str, required=True,
        help="Path to the trained YOLO .pt weights file."
    )
    parser.add_argument(
        "--dataset_dir", type=str, required=True,
        help="Path to the dataset root directory (must contain images/train/ and classes.txt)."
    )
    parser.add_argument(
        "--calib_samples", type=int, default=300,
        help="Number of calibration images used during MCT quantization."
    )

    return parser.parse_args()


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def get_classes(classes_file: str) -> list:
    """Read class names from classes.txt, stripping numeric index prefixes."""
    if not os.path.exists(classes_file):
        raise FileNotFoundError(
            f"classes.txt not found at '{classes_file}'.\n"
            "Expected format (one class per line, optional '0: ' prefix)."
        )

    classes = []
    with open(classes_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Strip optional numeric prefix (e.g. "0: open" -> "open")
            name = line.split(":", 1)[1].strip() if ":" in line else line
            classes.append(name)
    return classes


def prepare_calibration_subset(dataset_dir: str, calib_samples: int) -> str:
    """
    Copy up to `calib_samples` training images (and their labels) into a
    temporary calib_temp/ subfolder and return the relative folder name.
    """
    src_images = os.path.join(dataset_dir, "images", "train")
    src_labels = os.path.join(dataset_dir, "labels", "train")
    dst_images = os.path.join(dataset_dir, "images", "calib_temp")
    dst_labels = os.path.join(dataset_dir, "labels", "calib_temp")

    os.makedirs(dst_images, exist_ok=True)
    os.makedirs(dst_labels, exist_ok=True)

    images = glob(os.path.join(src_images, "*.jpg"))[:calib_samples]
    if not images:
        raise FileNotFoundError(
            f"No .jpg images found in '{src_images}'.\n"
            "Ensure training images exist before running the pipeline."
        )

    print(f"  -> Copying {len(images)} images to calibration subset...")
    for img_path in images:
        basename = os.path.basename(img_path)
        shutil.copy(img_path, os.path.join(dst_images, basename))

        label_name = os.path.splitext(basename)[0] + ".txt"
        label_src  = os.path.join(src_labels, label_name)
        if os.path.exists(label_src):
            shutil.copy(label_src, os.path.join(dst_labels, label_name))

    return "images/calib_temp"


def generate_calibration_yaml(dataset_dir: str, calib_folder: str, classes: list) -> str:
    """Write a temporary YAML file pointing to the calibration subset."""
    abs_dataset = os.path.abspath(dataset_dir).replace("\\", "/")

    yaml_lines = [
        f"path: {abs_dataset}\n",
        "train: images/train\n",
        f"val: {calib_folder}\n\n",
        "names:\n",
    ]
    for i, cls in enumerate(classes):
        yaml_lines.append(f"  {i}: '{cls}'\n")

    yaml_path = "auto_calibration_data.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.writelines(yaml_lines)

    return yaml_path


def cleanup(yaml_path: str, dataset_dir: str) -> None:
    """Remove the temporary YAML and calibration image/label folders."""
    if os.path.exists(yaml_path):
        os.remove(yaml_path)

    for subdir in ["images/calib_temp", "labels/calib_temp"]:
        path = os.path.join(dataset_dir, subdir)
        if os.path.exists(path):
            shutil.rmtree(path)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_arguments()

    print("\n" + "=" * 60)
    print("  Sony IMX500 Compilation Pipeline")
    print("=" * 60)

    # Step 1 — Prepare calibration data
    print("\n[1/4] Loading class names...")
    classes_file = os.path.join(args.dataset_dir, "classes.txt")
    classes = get_classes(classes_file)
    print(f"      Found {len(classes)} classes: {classes}")

    print(f"\n[2/4] Preparing calibration subset ({args.calib_samples} images)...")
    calib_folder = prepare_calibration_subset(args.dataset_dir, args.calib_samples)
    yaml_path    = generate_calibration_yaml(args.dataset_dir, calib_folder, classes)

    # Step 2 — Load model
    print(f"\n[3/4] Loading YOLO model from '{args.weights}'...")
    if not os.path.exists(args.weights):
        raise FileNotFoundError(f"Weights file not found: '{args.weights}'")
    model = YOLO(args.weights)

    # Step 3 — Export to IMX500
    print("\n[4/4] Running MCT quantization and IMX500 compilation...")
    try:
        model.export(format="imx", data=yaml_path)

        # Locate the output packerOut.zip
        model_dir  = os.path.dirname(args.weights)
        base_name  = os.path.splitext(os.path.basename(args.weights))[0]
        packer_zip = os.path.join(model_dir, f"{base_name}_imx_model", "packerOut.zip")

        if os.path.exists(packer_zip):
            print(f"\n[SUCCESS] Pipeline complete!")
            print(f"  Compiled model: {packer_zip}")
            print("  Transfer this .zip file to your Raspberry Pi and package it with imx500-package.")
        else:
            print(f"\n[ERROR] packerOut.zip not found at expected path: '{packer_zip}'")
            print("  Check Ultralytics export logs above for details.")

    finally:
        print("\nCleaning up temporary files...")
        cleanup(yaml_path, args.dataset_dir)


if __name__ == "__main__":
    main()
