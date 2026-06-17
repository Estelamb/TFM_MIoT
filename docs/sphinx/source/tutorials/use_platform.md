# Cómo Usar la Interfaz y Realizar Despliegues en AURA

Esta sección detalla cómo interactuar con el panel de administración web de AURA para registrar hardware, preparar artefactos de IA (modelos y scripts) y lanzar despliegues Over-the-Air (OTA).

---

## Modo Demostración (Demo Mode)

Si deseas probar y familiarizarte con el diseño y las funcionalidades de la interfaz gráfica sin necesidad de tener todo el ecosistema de backend o un dispositivo de hardware encendido, la interfaz cuenta con un **Modo Demostración**:

* Encontrarás un interruptor deslizante (**Demo Mode**) en la esquina inferior derecha del menú lateral.
* Al activarlo, la aplicación Next.js cargará datos simulados completos de dispositivos, telemetrías dinámicas y flujos de despliegue ficticios para facilitar la exploración de la interfaz.
* Al desactivarlo (modo real), se limpia el estado local y el frontend se comunicará directamente mediante HTTP y WebSocket con el `api-gateway` levantado en tu puerto `8000`.

---

## Flujo de Trabajo en Modo Real

Para realizar un despliegue de visión artificial real sobre un dispositivo perimetral, sigue los siguientes pasos organizados secuencialmente:

### Paso 1: Registrar un Dispositivo

1. En el panel lateral, dirígete a la sección **Devices** (Dispositivos).
2. Haz clic en el botón **Register Device** (Registrar dispositivo).
3. Introduce los siguientes datos obligatorios:
   * **Device ID**: El identificador único que configuraste en el agente perimetral (por ejemplo, `my-raspberry-01`). Debe coincidir de forma exacta para que se asocie correctamente.
   * **Name**: Un nombre amigable para identificar el dispositivo en las listas.
   * **Location**: Ubicación física del dispositivo (opcional).
   * **Hardware Type**: Selecciona el tipo de acelerador presente en la máquina (Hailo-8, AI Camera IMX500, CPU, etc.).
4. Guarda el registro. El estado inicial aparecerá como **Offline** hasta que enciendas el agente de edge configurado con ese mismo `Device ID`.

### Paso 2: Subir un Modelo de IA

1. Navega a la sección **Models** (Modelos) en el menú de navegación.
2. Haz clic en **Upload Model** (Subir modelo).
3. Rellena los detalles requeridos:
   * **Name**: Un nombre representativo (ej. `yolov8n-detect`).
   * **Version**: Etiqueta de versión (ej. `1.0.0`).
   * **Target Hardware**: El hardware para el cual está optimizado u optimizarás el modelo.
   * **Model File**: Selecciona el archivo binario del modelo en tu disco local (ej. un archivo de pesos PyTorch `.pt`).
4. Haz clic en **Submit**. El archivo se almacenará de manera segura en el bucket de MinIO S3 y se registrará en PostgreSQL.

### Paso 3: Subir un Script de Inferencia

Los scripts de inferencia definen el preprocesamiento, la llamada al modelo y el postprocesamiento en el agente perimetral.

1. Dirígete a la sección **Scripts** en el menú.
2. Haz clic en el botón **Upload Script**.
3. Rellena el formulario:
   * **Name**: Nombre único del script (ej. `yolo-detection-script`).
   * **Version**: Versión del script.
   * **File**: Sube tu script en formato `.py`. El script debe estructurarse conforme a la API del agente.

#### Ejemplo de Script de Inferencia Compatible
```python
from aura_hw import execute_inference
import numpy as np

def pre_inference(raw_input):
    # Transforma la imagen de entrada en un tensor NumPy
    # Ejemplo de procesamiento básico...
    return raw_input

def post_inference(raw_output):
    # Formatea los resultados a una estructura estructurada en JSON
    return [{"class": "person", "confidence": 0.89, "bbox": [100, 50, 250, 300]}]

def run(raw_input):
    # Esta es la función principal que ejecutará periódicamente el runtime de AURA
    processed_input = pre_inference(raw_input)
    raw_output = execute_inference(processed_input)
    return post_inference(raw_output)
```

### Paso 4: Crear y Lanzar un Despliegue

Una vez que cuentas con el dispositivo conectado, un modelo y un script en la plataforma, puedes unirlos en un **Despliegue**:

1. Ve a la sección **Deployments** (Despliegues).
2. Haz clic en el botón **New Deployment** (Nuevo despliegue).
3. Selecciona el **Dispositivo** de destino de la lista.
4. Selecciona el **Modelo** y el **Script** que deseas desplegar en dicho dispositivo.
5. Haz clic en **Deploy**.

#### ¿Qué ocurre por detrás al hacer esto?
1. El `api-gateway` recibe la petición y llama al `edge-connector-service`.
2. El conector emite una orden de despliegue codificada en JSON hacia el topic MQTT del dispositivo: `device/{id}/commands`.
3. El agente de Edge recibe la orden, descarga los archivos del modelo y del script directamente desde MinIO S3, valida sus hashes SHA-256 para evitar corrupción, carga el nuevo runtime en caliente y comienza a ejecutar el bucle de inferencia.
4. El agente responde con un evento de confirmación en `device/{id}/events`.

### Paso 5: Monitorización y Telemetría en Tiempo Real

1. Dirígete a la sección **Monitoring** (Monitorización) o haz clic sobre el dispositivo en la lista de dispositivos.
2. Podrás ver en tiempo real:
   * **Gráficas de recursos**: Consumo porcentual de CPU, uso de memoria RAM en MB/GB y estado de la red.
   * **Estado de ejecución**: Nombre de la versión del modelo y script activos en el hardware.
   * **Inference Live Stream**: Resultados de detección formateados en JSON que envía el agente mediante el topic MQTT de inferencia (`device/{id}/inference`).
