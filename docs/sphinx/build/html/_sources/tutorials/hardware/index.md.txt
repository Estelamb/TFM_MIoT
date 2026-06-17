# Hardware Tutorials

This section gathers step-by-step guides for hardware setup, model compilation, and local inference execution using different accelerators and devices supported by **AURA Platform**.

Select your target hardware configuration from the list below to access its specific tutorial:

* [Raspberry Pi 5 + Hailo-8 Accelerator](hailo8)
* [Raspberry Pi 5 + Hailo-8L Accelerator](hailo8l)
* [Raspberry Pi 5 + AI Camera (IMX500)](imx500)
* [Raspberry Pi 5 (CPU Inference via TFLite)](rpi_cpu)
* [NVIDIA Jetson Orin Nano](jetson_orin)

```{toctree}
:maxdepth: 1
:hidden:

hailo8
hailo8l
imx500
rpi_cpu
jetson_orin
```

---

> [!TIP]
> If you are developing a custom hardware backend not listed here, refer to the [Code Explanation](../../code_explanation) section to learn how to extend the `aura_hw` module and implement a new inference backend.
