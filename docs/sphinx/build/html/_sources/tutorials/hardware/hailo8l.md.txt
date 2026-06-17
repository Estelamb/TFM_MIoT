# Tutorial: Raspberry Pi 5 + Hailo-8L

*(This tutorial will be completed by the user. Placeholder reserved for the integration guide of Raspberry Pi 5 with the Hailo-8L module).*

## Introduction to Hailo-8L Hardware

The Hailo-8L deep learning processor delivers up to 13 TOPS. It is a cost-effective, low-power version of the Hailo NPU, commonly sold with the official Raspberry Pi AI Kit.

## Hardware Requirements and Connection

* Raspberry Pi 5.
* Raspberry Pi AI Kit (includes the Hailo-8L module pre-mounted on the official PCIe HAT and cooling).
* Flexible PCIe ribbon cable for Raspberry Pi 5.

## Configuration and Drivers

Steps to activate the Hailo-8L NPU on Raspberry Pi OS:

1. Perform a full system and firmware upgrade:
   ```bash
   sudo apt update && sudo apt full-upgrade -y
   ```
2. Install the official Hailo PCIe driver and utilities:
   ```bash
   sudo apt install hailort-pcie-driver-dkms hailort-cli
   ```
3. Reboot the board to load kernel modules.
4. Verify NPU detection:
   ```bash
   hailortcli fw-control identify
   ```

## Compilation and Execution in AURA

Details on how to compile `.hef` files optimized for the Hailo-8L architecture and how to run them in AURA.
