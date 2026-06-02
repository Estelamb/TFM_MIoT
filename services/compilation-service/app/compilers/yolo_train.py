"""
YOLO Training Pipeline
======================
Trains a YOLOv8n (or compatible) model on a custom dataset.
Supports fresh training, resuming, and validation-only modes.

Usage examples:
    # Fresh training
    python yolo_train.py --config configs/dataset_config.yaml --init_model yolov8n.pt --epochs 100 --name my_run

    # Resume training
    python yolo_train.py --init_model runs/detect/my_run/weights/last.pt --resume_training --name runs/detect/my_run

    # Validation only
    python yolo_train.py --init_model runs/detect/my_run/weights/best.pt --val_model --name my_run
"""

import argparse
from ultralytics import YOLO


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a YOLO object detection model.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # --- Dataset & model ---
    parser.add_argument(
        "--config", type=str, default="configs/dataset_config.yaml",
        help="Path to the dataset YAML config file (required for training)."
    )
    parser.add_argument(
        "--init_model", type=str, default="yolov8n.pt",
        help="Path to the initial model weights (.pt file)."
    )

    # --- Training parameters ---
    parser.add_argument(
        "--name", type=str, default="yolo_run",
        help="Name for the output run directory."
    )
    parser.add_argument(
        "--epochs", type=int, default=100,
        help="Number of training epochs."
    )
    parser.add_argument(
        "--image_size", type=str, default="640x640",
        help="Input image size as WxH (e.g. 640x640)."
    )
    parser.add_argument(
        "--device", type=int, default=0,
        help="GPU device index to use for training."
    )
    parser.add_argument(
        "--gpu_percent", type=float, default=0.9,
        help="Fraction of GPU RAM to use (passed as 'batch' to Ultralytics)."
    )

    # --- Operation modes ---
    parser.add_argument(
        "--resume_training", action="store_true",
        help="Resume training from --init_model checkpoint."
    )
    parser.add_argument(
        "--val_model", action="store_true",
        help="Run validation only — skip training."
    )

    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    # Parse image dimensions (WxH -> [H, W] for YOLO convention)
    image_w, image_h = map(int, args.image_size.split("x"))
    image_size = [image_h, image_w]
    print(f"[INFO] Image size (H x W): {image_size}")

    # Load model
    print(f"[INFO] Loading model from: {args.init_model}")
    model = YOLO(args.init_model)

    # --- Validation only ---
    if args.val_model:
        print("[INFO] Running validation only...")
        model.val(name=args.name, project=args.name)
        return

    # --- Training ---
    project = args.name if args.resume_training else "runs/detect"

    print(f"[INFO] Starting {'resumed' if args.resume_training else 'fresh'} training...")
    model.train(
        data=args.config,
        epochs=args.epochs,
        imgsz=image_size,
        device=args.device,
        name=args.name,
        batch=args.gpu_percent,
        resume=args.resume_training,
        cache=False,
        project=project,
        workers=0,
        save=True,
    )
    print(f"[INFO] Training complete. Results saved to: {project}/{args.name}")


if __name__ == "__main__":
    main()
