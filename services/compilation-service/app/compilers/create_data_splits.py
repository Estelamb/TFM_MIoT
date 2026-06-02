"""
Dataset Split Generator for YOLO Training
==========================================
Creates train / validation / test split .txt files and a YAML config
from a dataset organised as:

    <data_dir>/
    ├── images/
    │   ├── img1.jpg
    │   └── ...
    ├── labels/
    │   ├── img1.txt
    │   └── ...
    └── classes.json          # {"class_name": index, ...}

Output files (written to <data_dir>/ and <parent>/configs/):
    train.txt / train_onnx.txt
    val.txt   / val_onnx.txt
    test.txt  / test_onnx.txt
    configs/<basename>_config.yaml (or configs/<basename>_onnx_config.yaml)

Usage examples:
    # Standard split
    python create_data_splits.py --data_dir Models/MyModel/dataset

    # ONNX-calibration split (capped at 300 images per split)
    python create_data_splits.py --data_dir Models/MyModel/dataset --onnx_config

    # Custom ratios
    python create_data_splits.py --data_dir Models/MyModel/dataset --val_split 0.15 --test_split 0.15
"""

import argparse
import json
import os
import random
from typing import Any, Dict, List


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate train/val/test splits and a YOLO YAML config.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "--data_dir", type=str, required=True,
        help="Path to the dataset root directory (must contain images/ and classes.json)."
    )
    parser.add_argument(
        "--val_split", type=float, default=0.1,
        help="Fraction of images reserved for validation."
    )
    parser.add_argument(
        "--test_split", type=float, default=0.2,
        help="Fraction of images reserved for testing."
    )
    parser.add_argument(
        "--onnx_config", action="store_true",
        help="Generate a reduced split (max 300 images per set) for ONNX calibration."
    )

    return parser.parse_args()


def collect_image_paths(images_root: str) -> List[str]:
    """Recursively collect all image paths relative to images_root."""
    paths: List[str] = []
    for root, _, files in os.walk(images_root):
        for fname in files:
            abs_path = os.path.join(root, fname)
            rel_path = abs_path.replace(images_root, "./images")
            paths.append(rel_path + "\n")
    return paths


def load_classes(data_dir: str) -> Dict[str, Any]:
    """Load class definitions from classes.json."""
    class_file = os.path.join(data_dir, "classes.json")
    if not os.path.exists(class_file):
        raise FileNotFoundError(
            f"classes.json not found at '{class_file}'.\n"
            "Create it with format: {{\"class_name\": index, ...}}"
        )
    with open(class_file, "r", encoding="utf-8") as f:
        return json.load(f)


def write_split_files(
    data_dir: str,
    train: List[str],
    val: List[str],
    test: List[str],
    suffix: str,
) -> tuple:
    """Write split .txt files and return their paths."""
    train_path = os.path.join(data_dir, f"train{suffix}.txt")
    val_path   = os.path.join(data_dir, f"val{suffix}.txt")
    test_path  = os.path.join(data_dir, f"test{suffix}.txt")

    for path, lines in [(train_path, train), (val_path, val), (test_path, test)]:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(lines)

    return train_path, val_path, test_path


def write_yaml_config(
    data_dir: str,
    train_path: str,
    val_path: str,
    test_path: str,
    classes: Dict[str, Any],
    suffix: str,
) -> str:
    """Generate and write a YOLO-compatible YAML config file."""
    basename   = os.path.basename(os.path.normpath(data_dir))
    parent_dir = os.path.dirname(os.path.normpath(data_dir))
    config_dir = os.path.join(parent_dir, "configs")
    os.makedirs(config_dir, exist_ok=True)

    yaml_path = os.path.join(config_dir, f"{basename}{suffix}_config.yaml")

    def to_posix(p: str) -> str:
        return p.replace("\\", "/")

    lines = [
        "# Train images - path to training split file\n",
        f"train: {to_posix(train_path)}\n\n",
        "# Validation images - path to validation split file\n",
        f"val: {to_posix(val_path)}\n\n",
        "# Test images - path to test split file\n",
        f"test: {to_posix(test_path)}\n\n",
        f"# Number of classes\n",
        f"nc: {len(classes)}\n\n",
        f"# Class names\n",
        f"names: {list(classes.keys())}\n",
    ]

    with open(yaml_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    return yaml_path


def main() -> None:
    args = parse_arguments()

    # --- Collect & shuffle images ---
    images_root = os.path.join(args.data_dir, "images")
    if not os.path.isdir(images_root):
        raise NotADirectoryError(f"Images directory not found: '{images_root}'")

    all_paths = collect_image_paths(images_root)
    if not all_paths:
        raise ValueError(f"No images found under '{images_root}'")

    random.shuffle(all_paths)
    total = len(all_paths)
    print(f"[INFO] Found {total} images in '{images_root}'")

    # --- Compute split sizes ---
    n_test = int(args.test_split * total)
    n_val  = int(args.val_split  * total)

    test_images  = [all_paths.pop() for _ in range(n_test)]
    val_images   = [all_paths.pop() for _ in range(n_val)]
    train_images = all_paths  # remainder

    # --- Cap sizes for ONNX calibration ---
    suffix = ""
    if args.onnx_config:
        suffix = "_onnx"
        ONNX_CAP = 300
        train_images = train_images[:ONNX_CAP]
        val_images   = val_images[:ONNX_CAP]
        test_images  = test_images[:ONNX_CAP]
        print(f"[INFO] ONNX mode: capped each split to {ONNX_CAP} images")

    print(f"[INFO] Split — train: {len(train_images)}, val: {len(val_images)}, test: {len(test_images)}")

    # --- Load classes ---
    classes = load_classes(args.data_dir)
    print(f"[INFO] Loaded {len(classes)} classes: {list(classes.keys())}")

    # --- Write files ---
    train_path, val_path, test_path = write_split_files(
        args.data_dir, train_images, val_images, test_images, suffix
    )
    yaml_path = write_yaml_config(
        args.data_dir, train_path, val_path, test_path, classes, suffix
    )

    print(f"[INFO] Split files written to:  '{args.data_dir}'")
    print(f"[INFO] YAML config written to:  '{yaml_path}'")


if __name__ == "__main__":
    main()
