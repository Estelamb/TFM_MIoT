# Tutorial: Raspberry Pi 5 (CPU - TFLite)

*(Este tutorial será redactado por el usuario. Espacio reservado para la guía de ejecución de inferencia en CPU de Raspberry Pi usando TFLite).*

## Introducción a la inferencia en CPU

Cuando no se dispone de un chip coprocesador acelerador de red (NPU/TPU), AURA puede hacer uso de la CPU del dispositivo corriendo modelos en formato TensorFlow Lite (`.tflite`). Si bien el rendimiento es inferior comparado con las NPUs dedicada, es ideal para pruebas, depuración y modelos ligeros.

## Requisitos de Software

* Tener instalado Python 3.10+ en la Raspberry Pi.
* Instalar el runtime de TensorFlow Lite:
  ```bash
  pip install tflite-runtime
  ```

## Uso del backend en AURA

El runtime de `aura_hw` detecta automáticamente que no hay aceleradores y conmuta por defecto al backend CPU. Para configurar manualmente esta opción, define la variable de entorno:

```bash
AURA_HARDWARE_TYPE=rpi
```

Añade aquí los detalles del flujo de trabajo y benchmarks de rendimiento que consideres pertinentes.
