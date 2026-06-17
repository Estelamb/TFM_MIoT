# Tutorial: Raspberry Pi 5 + Hailo-8

*(Este tutorial será redactado por el usuario. Espacio reservado para la guía de integración de Raspberry Pi 5 con el módulo Hailo-8).*

## Introducción al hardware Hailo-8

El procesador de aprendizaje profundo (NPU) Hailo-8 ofrece hasta 26 TOPS para tareas de inteligencia artificial en el borde. En esta sección puedes describir cómo se conecta y se comporta el dispositivo en la plataforma AURA.

## Requisitos de Hardware y Conexión

* Raspberry Pi 5 con fuente de alimentación adecuada.
* Shield PCIe (como el de Pineberry Pi, Raspberry Pi original u otros fabricantes).
* Módulo Hailo-8 M.2 Key M.
* Disipador de calor y ventilador (altamente recomendado).

## Configuración del Sistema Operativo y Controladores

Instrucciones paso a paso para configurar la Raspberry Pi 5 para habilitar la interfaz PCIe y detectar la NPU:

1. Modificar `/boot/firmware/config.txt`:
   ```ini
   dtparam=pciex1
   # Habilitar velocidad Gen 3 si es soportado
   dtparam=pciex1_gen=3
   ```
2. Instalar el driver de kernel y las utilidades `hailortcli`:
   ```bash
   # Comandos de instalación del firmware y dkms...
   ```
3. Comprobar la detección del hardware:
   ```bash
   hailortcli fw-control identify
   ```

## Compilación de Modelos para Hailo-8

Pasos para compilar modelos desde la interfaz de AURA o usando la CLI de Hailo Software Suite (DFG) para generar archivos `.hef`.

## Script de Inferencia en AURA

Ejemplo de script que consume el backend Hailo-8:

```python
# Introduce aquí el ejemplo de código de inferencia adaptado para Hailo-8
```
