# Tutorial: NVIDIA Jetson Orin Nano

*(Este tutorial será redactado por el usuario. Espacio reservado para la guía de integración y ejecución de inferencia en NVIDIA Jetson Orin Nano usando TensorRT).*

## Introducción a NVIDIA Jetson Orin Nano

La plataforma NVIDIA Jetson Orin Nano cuenta con una GPU basada en la arquitectura NVIDIA Ampere y aceleradores de aprendizaje profundo que ofrecen hasta 40 TOPS de rendimiento de IA. Permite ejecutar modelos complejos en formatos optimizados mediante TensorRT (`.engine`).

## Requisitos de Hardware y Entorno

* NVIDIA Jetson Orin Nano Developer Kit (o módulo equivalente en placa portadora).
* Tarjeta microSD o unidad SSD NVMe con **JetPack 6.0** o superior instalado.
* Python 3.10+ y la biblioteca `tensorrt` instalada a través de JetPack.

## Detección y Configuración

AURA detecta la plataforma leyendo la release del sistema y la presencia del archivo `/etc/nv_tegra_release`.

Puedes forzar el backend configurando la variable de entorno:
```bash
AURA_HARDWARE_TYPE=jetson_orin_nano
```

Escribe en esta sección las guías detalladas para compilar y desplegar modelos en formato TensorRT `.engine` desde el backend de AURA.
