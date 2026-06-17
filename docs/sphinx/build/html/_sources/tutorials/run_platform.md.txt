# Cómo Ejecutar la Plataforma AURA y el Agente de Edge

Esta guía proporciona un paso a paso detallado para poner en marcha tanto la infraestructura central de servicios (Backend, Frontend y Base de Datos) como el agente local que corre en el hardware perimetral.

---

## 1. Requisitos Previos

Antes de comenzar la instalación, asegúrate de contar con los siguientes elementos en tu sistema host o servidor:

* **Docker Engine** (versión 24 o superior) junto con **Docker Compose v2**.
* Un mínimo de **8 GB de RAM** disponibles (se recomienda 16 GB si se están compilando múltiples modelos pesados de forma simultánea).
* Los siguientes puertos de red libres en el host:
  * `3000` (Frontend en Next.js)
  * `8000` (API Gateway / Docs Swagger)
  * `1883` (Broker MQTT Mosquitto)
  * `5432` (PostgreSQL)
  * `9000` y `9001` (Servidor de almacenamiento MinIO S3 y Consola de administración)
  * `27017` (MongoDB)
  * `50051–50053` (Puertos gRPC internos para comunicación entre servicios)
  * `9100` (Exportador de métricas para Prometheus)

---

## 2. Configurar el Entorno del Servidor

AURA utiliza variables de entorno declaradas en un archivo `.env` en la raíz del proyecto para inicializar las contraseñas, secretos y URIs de conexión.

1. Duplica la plantilla de variables de entorno de ejemplo:
   ```bash
   cp .env.example .env
   ```

2. Genera una clave secreta segura para JWT e introdúcela en el archivo `.env`:
   ```bash
   # Generar clave aleatoria
   openssl rand -hex 32
   ```
   Abre el archivo `.env` y busca la línea `SECRET_KEY`. Reemplaza su valor por la clave aleatoria que acabas de generar.

> [!NOTE]
> Para el desarrollo en local, los valores por defecto configurados en `.env.example` funcionan directamente sin necesidad de modificaciones adicionales.

---

## 3. Levantar los Servicios de la Plataforma

Para compilar las imágenes e iniciar la plataforma completa en segundo plano (modo detached), ejecuta el siguiente comando en la raíz del proyecto:

```bash
docker compose up -d
```

* **Nota**: La primera ejecución puede demorar entre **3 y 5 minutos** debido a que Docker debe descargar las imágenes base y compilar los contenedores locales de cada microservicio.

Una vez que termine la ejecución, comprueba que todos los servicios estén levantados y saludables:

```bash
docker compose ps
```

Deberías ver una salida en la que los contenedores `api-gateway`, `registry-service`, `mlops-service`, `edge-connector-service`, `postgres`, `mongodb`, `mosquitto`, `minio` y `frontend` se muestren con el estado `Up` o `Running`.

### Direcciones de Acceso Útiles

| Servicio | URL / Dirección | Credenciales por Defecto |
|---|---|---|
| **Consola Frontend** | [http://localhost:3000](http://localhost:3000) | Usuario: `admin` / Contraseña: `aura2026` |
| **API Docs (Swagger)** | [http://localhost:8000/docs](http://localhost:8000/docs) | Requiere inicio de sesión previo en el endpoint `/auth/token` |
| **Consola MinIO** | [http://localhost:9001](http://localhost:9001) | Usuario: `aura` / Contraseña: `aura_dev` |
| **Métricas Prometheus** | [http://localhost:9100/metrics](http://localhost:9100/metrics) | Acceso anónimo |

---

## 4. Resolución de Problemas y Visualización de Logs

Si alguno de los servicios falla o no arranca correctamente, puedes inspeccionar los logs en tiempo real:

```bash
# Ver los logs combinados de todos los contenedores en tiempo real
docker compose logs -f

# Filtrar los logs únicamente para un servicio concreto (ej. API Gateway)
docker compose logs -f api-gateway

# Filtrar logs para el conector de edge
docker compose logs -f edge-connector-service
```

---

## 5. Ejecutar el Agente de Edge en un Dispositivo Físico

El agente de edge es el encargado de comunicarse con AURA Platform para recibir instrucciones de despliegue y reportar telemetría. Debe ejecutarse en el dispositivo físico de destino (por ejemplo, una Raspberry Pi 5).

### 1. Copiar los archivos al dispositivo perimetral
Transfiere la carpeta `edge-runtime/` de la plataforma AURA al almacenamiento local de tu dispositivo edge (mediante `scp`, `rsync` o clonando el repositorio directamente en el dispositivo).

### 2. Instalar dependencias en el dispositivo
El agente de edge requiere de Python 3.10 o superior. Instala las dependencias necesarias:

```bash
# Navegar a la carpeta del runtime
cd edge-runtime

# Instalar librerías requeridas
pip install -r requirements.txt
```

* **Importante**: Si planeas usar aceleradores específicos como Hailo-8, asegúrate de que el SDK y el controlador del fabricante (ej. HailoRT) estén instalados en el sistema operativo del dispositivo perimetral antes de arrancar el agente.

### 3. Iniciar el Agente con Variables de Entorno
Inicia el script de arranque `agent.py` proporcionando las variables del entorno mediante la consola:

```bash
AURA_DEVICE_ID=my-raspberry-01 \
AURA_MQTT_HOST=192.168.1.50 \
AURA_MQTT_PORT=1883 \
AURA_HARDWARE_TYPE=hailo8 \
AURA_TELEMETRY_INTERVAL=10 \
python agent.py
```

#### Parámetros de Configuración del Agente

| Variable | Valor por Defecto | Descripción |
|---|---|---|
| `AURA_DEVICE_ID` | `dev-device-001` | El identificador único del dispositivo. Debe coincidir exactamente con el ID que registres en la consola web de AURA. |
| `AURA_MQTT_HOST` | `localhost` | La dirección IP o nombre DNS donde se ejecuta el broker MQTT de la plataforma. |
| `AURA_MQTT_PORT` | `1883` | Puerto de escucha del broker MQTT (usualmente `1883`). |
| `AURA_HARDWARE_TYPE` | *Auto-detectado* | Sobrescribe la detección automática del hardware perimetral. Valores válidos: `hailo8`, `hailo8l`, `imx500`, `rpi` (CPU), `jetson_orin_nano`. |
| `AURA_TELEMETRY_INTERVAL` | `10` | Frecuencia en segundos con la que el agente envía telemetría de CPU y RAM a la nube. |

El agente buscará establecer una conexión con la plataforma. Al tener éxito, el dispositivo se mostrará como **Conectado (Online)** en la interfaz de usuario de AURA.
