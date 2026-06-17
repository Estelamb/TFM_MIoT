# Tutorial: Raspberry Pi 5 + Hailo-8L

*(Este tutorial será redactado por el usuario. Espacio reservado para la guía de integración de Raspberry Pi 5 con el módulo Hailo-8L).*

## Introducción al hardware Hailo-8L

El procesador de aprendizaje profundo Hailo-8L (M.2 Key B+M / M.2 Key M) ofrece hasta 13 TOPS. Es la versión optimizada en consumo y coste de la NPU Hailo, comúnmente vendida con el kit Raspberry Pi AI Kit.

## Requisitos de Hardware y Conexión

* Raspberry Pi 5.
* Raspberry Pi AI Kit (incluye el módulo Hailo-8L montado sobre el HAT PCIe oficial y el disipador).
* Cable plano PCIe flexible para Raspberry Pi 5.

## Configuración y Controladores

Instrucciones para activar la NPU Hailo-8L en Raspberry Pi OS:

1. Ejecutar la actualización completa del firmware y sistema:
   ```bash
   sudo apt update && sudo apt full-upgrade -y
   ```
2. Instalar el driver oficial de Hailo y dependencias:
   ```bash
   sudo apt install hailort-pcie-driver-dkms hailort-cli
   ```
3. Reiniciar la placa para cargar los drivers de kernel.
4. Identificar la NPU:
   ```bash
   hailortcli fw-control identify
   ```

## Compilación y Ejecución en AURA

Detalles sobre cómo compilar archivos `.hef` específicos para la arquitectura Hailo-8L y cómo configurar el runtime en la plataforma.
