@echo off
setlocal enabledelayedexpansion

:: Automatically change the working directory to the project root (parent directory of scripts/)
cd /d "%~dp0.."

echo =====================================================================
echo              AURA Platform - GPU Training Setup Script
echo =====================================================================
echo This script will configure your local Python environment to run
echo YOLO training on your computer's NVIDIA GPU.
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to your system PATH.
    echo Please install Python 3.10, 3.11, or 3.12 before running this script.
    pause
    exit /b 1
)

:: Create virtual environment if it doesn't exist in the project root
if not exist ".venv" (
    echo [INFO] Creating Python virtual environment in .venv...
    python -m venv .venv
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [SUCCESS] Virtual environment created.
) else (
    echo [INFO] Found existing virtual environment in .venv.
)

:: Activate the virtual environment
echo [INFO] Activating virtual environment...
call .venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)

:: Upgrade pip
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip

:: Install CUDA-enabled PyTorch
echo [INFO] Installing CUDA-enabled PyTorch (CUDA 12.1)...
echo This might take several minutes depending on your internet connection.
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install PyTorch.
    pause
    exit /b 1
)
echo [SUCCESS] PyTorch installed successfully.

:: Install Ultralytics
echo [INFO] Installing Ultralytics YOLO...
pip install ultralytics
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Ultralytics.
    pause
    exit /b 1
)
echo [SUCCESS] Ultralytics installed successfully.

echo.
echo =====================================================================
echo                    Verifying GPU / CUDA Status
echo =====================================================================
python -c "import torch; print('PyTorch version:', torch.__version__); print('CUDA available in PyTorch:', torch.cuda.is_available()); print('GPU Device Name:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')"
echo.

:: Check result of verification
python -c "import torch; exit(0 if torch.cuda.is_available() else 1)"
if %errorlevel% neq 0 (
    echo [WARNING] PyTorch was installed, but CUDA GPU was NOT detected.
    echo Make sure you have a compatible NVIDIA GPU and that the latest
    echo NVIDIA Drivers are installed on your computer.
) else (
    echo [SUCCESS] GPU setup verified! Training will run on your local GPU.
)

echo.
echo =====================================================================
echo How to run your training script:
echo 1. Keep this virtual environment activated (or run '.venv\Scripts\activate' in your shell)
echo 2. Run the script:
echo    python scripts\yolo_train.py --data_dir ^<path_to_your_dataset^> --epochs 20
echo.
echo Example with your specific dataset path:
echo    python scripts\yolo_train.py --data_dir "C:\Users\Estela\Desktop\Training\Models\Forgotten_Objects\dataset" --epochs 20
echo =====================================================================
echo.
pause
