# Raspberry Pi Camera Module 3 Integration Guide

This guide provides step-by-step instructions for physically connecting, configuring, verifying, and programmatically accessing the Raspberry Pi Camera Module 3 (standard or Wide version) on a Raspberry Pi 5.

This guide is based on the official `Raspberry Pi Camera hardware` [1] documentation and the `Picamera2 Python library` [2] documentation.

---

## 1. Physical Connection

The Raspberry Pi 5 uses high-density (mini-CSI) connectors for cameras, which are smaller than the standard CSI connectors used on the Raspberry Pi 4.

### Cable Requirements
* You must use a **Raspberry Pi 5 Camera Adapter Cable** [3] (high-density mini-CSI connector on the Raspberry Pi 5 side to standard CSI connector on the Camera Module 3 side).
* Note that standard DSI (display) and CSI (camera) adapter cables look similar but have different pin mappings. Ensure you are using the camera adapter cable.

### Connection Steps
1. Power down your Raspberry Pi 5 completely.
2. Locate one of the two dual-purpose **CAM/DISP** ports on the Raspberry Pi 5 board (labeled `CAM/DISP 0` and `CAM/DISP 1`).
3. Gently pull up the plastic locking collar of the CAM/DISP port.
4. Insert the mini-CSI ribbon cable with the **silver contact pins facing the HDMI/USB-C ports** (towards the center of the board) and the blue backing facing away.
5. Push the locking collar down to secure the cable.
6. Connect the other end of the cable to the Camera Module 3 board, ensuring the silver contacts face the back of the camera sensor board.

---

## 2. OS & Firmware Configuration

Ensure your operating system is up to date and has the correct device tree configurations enabled.

### Update the System

Execute the following commands in the terminal of your Raspberry Pi:

```bash
sudo apt update && sudo apt full-upgrade -y
sudo rpi-eeprom-update -a
sudo reboot
```

### Auto-detection Verification

Raspberry Pi OS Bookworm automatically loads the device overlays for native cameras. Ensure that auto-detection is enabled in your boot config:

1. Open `/boot/firmware/config.txt` in an editor:
   ```bash
   sudo nano /boot/firmware/config.txt
   ```
2. Verify that the following line is present and not commented out:
   ```ini
   camera_auto_detect=1
   ```
3. Save and close the file (Ctrl+O, Enter, Ctrl+X). If you made changes, reboot the system:
   ```bash
   sudo reboot
   ```

---

## 3. Verifying Camera Detection

Once the system reboots, check if the operating system detects the Camera Module 3 correctly.

Run the listing command in your terminal:

```bash
rpicam-still --list-cameras
```

### Expected Output
If detected, the output will look similar to this:

```text
Available cameras
-----------------
0 : imx708 [4608x2592] (/base/soc/i2c0mux/i2c@1/imx708@1a)
    Modes: 'SRGGB10_sensor_mode' : 1536x864 [120.00 fps]
           'SRGGB10_sensor_mode' : 2304x1296 [56.00 fps]
           'SRGGB10_sensor_mode' : 4608x2592 [14.00 fps]
```

> [!NOTE]
> The Camera Module 3 uses the Sony `imx708` sensor. Seeing `imx708` confirms the camera is detected.

---

## 4. Testing the Capture Pipeline

Verify that the camera can capture frames and show previews using the CLI camera tools.

### Test Image Capture

Capture a test picture and save it to the home directory:

```bash
rpicam-still -o ~/test_image.jpg
```

### Test Video Preview

Run a 10-second test video stream to inspect focus and lens orientation (requires a connected desktop interface or X-forwarding):

```bash
rpicam-hello -t 10000
```

---

## 5. Python Integration (Picamera2)

`Picamera2` is the modern Python interface for Raspberry Pi cameras, replacing the legacy `picamera` library on Bookworm.

### Install Dependencies

Install the library packages using apt:

```bash
sudo apt install python3-picamera2 python3-opencv -y
```

### Standalone Test Script

Create a Python script named `test_cam.py` to capture a frame programmatically:

```python
import time
from picamera2 import Picamera2

# 1. Initialize Picamera2 context
print("Initializing camera...")
picam2 = Picamera2()

# 2. Configure capture parameters (RGB888 stream)
config = picam2.create_preview_configuration(
    main={"size": (1920, 1080), "format": "RGB888"}
)
picam2.configure(config)

# 3. Start the camera stream
picam2.start()
print("Camera stream started. Waiting 2 seconds for auto-exposure...")
time.sleep(2)  # Allow sensor settings to settle

# 4. Capture a frame and save to disk
output_file = "python_capture.jpg"
picam2.capture_file(output_file)
print(f"Frame captured successfully and saved to: {output_file}")

# 5. Stop camera context
picam2.stop()
print("Camera released. Exit.")
```

Run the script:

```bash
python test_cam.py
```

---

## 6. Troubleshooting Common Gotchas

* **No camera detected (`Available cameras` is empty)**:
  - Check the ribbon cable orientation. The silver pins *must* face the HDMI ports on the Raspberry Pi 5 side.
  - Verify that the ribbon cable is inserted into a port configured for camera inputs. On Raspberry Pi 5, both CSI ports support cameras, but they must be clean and locked tightly.
  - Ensure you are not using a DSI display ribbon cable by mistake.
* **`vcgencmd get_camera` returns `supported=0 detected=0`**:
  - This is expected behavior on Raspberry Pi OS Bookworm. `vcgencmd` only queries the legacy firmware-based camera driver, which is disabled. Use `rpicam-still --list-cameras` instead.
* **Camera is busy or resource temporarily unavailable**:
  - Another process (such as a background script or streaming server) is accessing the camera sensor. Release the resource or reboot the system.

---

## References

* [1] Raspberry Pi Camera Hardware Overview: <https://www.raspberrypi.com/documentation/computers/camera_software.html>
* [2] Official Picamera2 Python Library API: <https://www.raspberrypi.com/documentation/computers/camera_software.html#picamera2>
* [3] Raspberry Pi 5 Mini-CSI Camera Cables: <https://www.raspberrypi.com/products/camera-adapter-cable/>

[1]: https://www.raspberrypi.com/documentation/computers/camera_software.html
[2]: https://www.raspberrypi.com/documentation/computers/camera_software.html#picamera2
[3]: https://www.raspberrypi.com/products/camera-adapter-cable/
