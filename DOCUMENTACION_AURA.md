# Documentación Técnica Detallada de la Plataforma AURA

Este documento proporciona una especificación técnica de grano fino sobre el funcionamiento interno de la plataforma **AURA**, detallando la arquitectura de microservicios, las bases de datos utilizadas, la comunicación por gRPC y MQTT, la inicialización del Edge Runtime y las metodologías para extender el sistema con nuevo hardware y periféricos.

---

## 1. Arquitectura de Microservicios en Detalle

La plataforma AURA se compone de un frontend moderno que interactúa con un **API Gateway** mediante peticiones REST tradicionales, el cual actúa como proxy inverso distribuyendo las cargas de control de forma asíncrona hacia microservicios backend consolidados que se comunican vía **gRPC**. Las tareas de procesamiento intensivo de datos (entrenamiento e inferencia local en compilación) se delegan mediante una arquitectura de colas basada en **Redis** y trabajadores **arq**.

```
TFM_MIoT/
├── services/
│   ├── api-gateway/            # Entrada HTTP y enrutado JWT
│   ├── registry-service/       # Inventario de dispositivos, modelos y scripts (Postgres)
│   ├── mlops-service/          # Entrenamiento YOLO y compilación de modelos (Redis + arq)
│   └── edge-connector-service/ # Despliegues OTA, telemetría y monitorización (MQTT + Mongo + Prometheus)
```

---

### 1.1. API Gateway (`api-gateway`)

* **Directorio principal**: `services/api-gateway/`
* **Tecnología**: FastAPI (Python 3.11/3.12), AsyncIO, Uvicorn, Python gRPC (asyncio), MinIO Python SDK.

#### Funciones y Responsabilidades
1. **Punto Único de Entrada HTTP**: Toda la comunicación HTTP entre el frontend y la plataforma pasa por el Gateway. Define middlewares para CORS y decodificación de tokens JWT.
2. **Autenticación y Autorización**:
   * Implementa OAuth2 con flujo de contraseña (`OAuth2PasswordRequestForm`).
   * Valida credenciales contra un usuario demostrativo configurado en `jwt.py` (`admin` / `aura2026`).
   * Genera tokens JWT firmados con clave secreta (`create_token()`). El middleware `verify_token` intercepta y valida las cabeceras `Authorization: Bearer <token>` de las rutas bajo `/api/*`.
3. **Gestión de Ficheros Grandes (MinIO)**: Para evitar cuellos de botella y sobrecargas de memoria en las llamadas gRPC, el Gateway se conecta directamente al cliente MinIO en el arranque (`lifespan` en `main.py`). Se encarga de recibir cargas multipart de ficheros binarios (`UploadFile`) y guardarlas directamente en los buckets:
   * `models`: Para archivos `.pt` (PyTorch/YOLO) subidos o entrenados.
   * `compiled`: Para binarios optimizados específicos de hardware (`.hef`, `.imx`, `.engine`, `.tflite`).
   * `scripts`: Para scripts de inferencia de Python (`.py`).
   * `datasets`: Para archivos de entrenamiento empaquetados en `.zip`.
   * `base-models`: Modelos preentrenados oficiales de YOLO para transferencia de aprendizaje.
4. **Proxy HTTP a gRPC**: Convierte las peticiones JSON entrantes en mensajes serializados Protobuf y las reenvía a través de stubs asíncronos a los puertos y servicios correspondientes.

#### Endpoints HTTP y Enrutado
* **Autenticación**:
  * `POST /auth/token` $\rightarrow$ Valida credenciales $\rightarrow$ Genera token JWT.
  * `GET /health` $\rightarrow$ Comprobación de estado general.
* **Dispositivos (`/api/devices`)**:
  * `POST /` $\rightarrow$ Registra un dispositivo (Llama a `CreateDevice` en `registry-service:50051`).
  * `GET /` $\rightarrow$ Lista todos los dispositivos (Llama a `ListDevices` en `registry-service:50051`).
  * `GET /{device_id}` $\rightarrow$ Recupera un dispositivo específico.
  * `DELETE /{device_id}` $\rightarrow$ Elimina el registro del dispositivo.
  * `GET /hardware-types` $\rightarrow$ Lista plataformas soportadas por los compiladores instalados (Llama a `GetSupportedHardware` en `mlops-service:50052`).
  * `GET /sensors` $\rightarrow$ Lista sensores (Llama a `GetSupportedSensors` en `mlops-service:50052`).
  * `GET /actuators` $\rightarrow$ Lista actuadores (Llama a `GetSupportedActuators` en `mlops-service:50052`).
* **Modelos de IA (`/api/models`)**:
  * `GET /base-model-options` $\rightarrow$ Lista modelos base en MinIO (`base-models`).
  * `GET /base-models/{filename}/download` $\rightarrow$ URL de descarga firmada para modelos base.
  * `POST /` $\rightarrow$ Sube metadatos y fichero de modelo a MinIO, y llama a `UploadModel` en `registry-service:50051`. Si `compile=true`, ejecuta asíncronamente `CompileModel` en `mlops-service:50052`.
  * `GET /` $\rightarrow$ Lista modelos disponibles.
  * `GET /{model_id}` $\rightarrow$ Información del modelo e histórico de compilación.
  * `PUT /{model_id}` $\rightarrow$ Modifica metadatos del modelo.
  * `DELETE /{model_id}` $\rightarrow$ Cancela cualquier trabajo activo en Redis y borra el modelo.
  * `POST /train` $\rightarrow$ Registra el modelo e inicia el entrenamiento YOLO llamando a `TrainModel` en `mlops-service:50052`.
  * `GET /{model_id}/logs` $\rightarrow$ Endpoint SSE (Server-Sent Events) que lee la lista de logs de Redis (`train_logs:{model_id}_list`) y se suscribe al canal PubSub de Redis (`train_logs:{model_id}`) para enviar trazas de entrenamiento en tiempo real al navegador.
* **Datasets (`/api/datasets`)**:
  * `POST /` $\rightarrow$ Registra metadatos en `registry-service:50051`.
  * `POST /{dataset_id}/upload` $\rightarrow$ Recibe el zip de dataset y lo sube a MinIO (`SetDatasetFile`).
* **Scripts de Inferencia (`/api/scripts`)**:
  * `POST /` $\rightarrow$ Recibe script Python, lo sube a MinIO y registra metadatos en `registry-service:50051`.
  * `GET /` $\rightarrow$ Lista scripts.
* **Despliegues (`/api/deployments`)**:
  * `POST /` $\rightarrow$ Crea despliegue en base de datos de `edge-connector-service:50053`. Si el modelo ya está compilado para la arquitectura del dispositivo, genera URLs firmadas y publica por MQTT. Si no está compilado, encola un flujo de compilación automática en `mlops-service` y posterior despliegue.
* **Monitorización (`/api/monitoring`)**:
  * `GET /devices` $\rightarrow$ Obtiene último estado, consumo de CPU/RAM y modelo/script cargado en los dispositivos (Llama a `ListDeviceStates` en `edge-connector-service:50053`).
  * `GET /devices/{device_id}/inference` $\rightarrow$ Devuelve las últimas predicciones JSON generadas por el dispositivo en campo (Llama a `GetInferenceResults` en `edge-connector-service:50053`).

---

### 1.2. Registry Service (`registry-service`)

* **Directorio principal**: `services/registry-service/`
* **Base de datos relacional**: PostgreSQL (Tablas `devices`, `datasets`, `models`, `scripts`)
* **Puerto gRPC**: `50051`

#### Modelo ORM (`models/orm.py`)
Consolida todas las entidades relacionales en un único esquema bajo la misma conexión SQLAlchemy:
* **Tabla `devices`**:
  * `id`: Clave primaria UUID.
  * `name`: Nombre descriptivo (String).
  * `hardware_type`: Arquitectura física (e.g. `"rpi"`, `"hailo8"`, `"simulated"`).
  * `description`: Texto libre descriptivo.
  * `status`: Estado de red (`"online"`, `"offline"`).
  * `last_seen_at`: Timestamp UTC de la última telemetría.
  * `created_at`: Fecha de registro en la plataforma.
  * `sensors`: Array de Strings (`ARRAY(String)`) que almacena los componentes sensores autorizados (e.g. `["camera_0", "env_sensor_0"]`).
  * `actuators`: Array de Strings (`ARRAY(String)`) de componentes actuadores declarados.
* **Tabla `datasets`**:
  * `id`: Clave primaria UUID.
  * `name`: Nombre del dataset.
  * `description`: Notas sobre el dataset.
  * `object_key`: Ubicación del fichero ZIP en MinIO.
  * `sha256`: Hash del zip.
  * `size_bytes`: Tamaño del fichero de dataset.
  * `meta_info`: Información extra (JSON).
  * `created_at`: Marca de tiempo.
* **Tabla `models`**:
  * `id`: Clave primaria UUID.
  * `name`: Nombre del modelo.
  * `description`: Detalles del modelo.
  * `source_key`: Referencia del fichero de pesos original `.pt` en MinIO.
  * `source_sha256`: Hash SHA-256 de los pesos de origen.
  * `compiled_key`: Referencia del binario optimizado en MinIO.
  * `compiled_sha256`: Hash SHA-256 del binario compilado.
  * `hardware_type`: Arquitectura hardware destino para la que se ha compilado.
  * `compile_status`: Estado de compilación actual (`"pending"`, `"training"`, `"compiling"`, `"ready"`, `"failed"`).
  * `compile_error`: Trazas de error.
  * `dataset_id`: Relación externa (FK) opcional a `datasets.id`.
  * `base_architecture`: Nombre del modelo preentrenado de origen.
  * `epochs`, `input_size`, `batch_size`: Parámetros de entrenamiento.
* **Tabla `scripts`**:
  * `id`: Clave primaria UUID.
  * `name`: Nombre descriptivo del script.
  * `description`: Funcionalidad del script.
  * `hardware_type`: Hardware objetivo.
  * `script_key`: Key del script `.py` en MinIO.
  * `script_sha256`: Hash del script.

#### Interfaz gRPC
Arranca un servidor gRPC asíncrono y expone simultáneamente tres servicios en el puerto `50051`:
* **`DeviceService`** (`grpc_handlers/device_handler.py`)
* **`AIService`** (`grpc_handlers/ai_handler.py`)
* **`ScriptService`** (`grpc_handlers/script_handler.py`)

---

### 1.3. MLOps Service (`mlops-service`)

* **Directorio principal**: `services/mlops-service/`
* **Tecnología**: gRPC Server, arq Redis-based Task Queue, Redis PubSub.
* **Puerto gRPC**: `50052`

#### Interfaz gRPC (`shared/proto/compilation.proto`)
Expone stubs para disparar entrenamientos y compilaciones, y recuperar el catálogo de hardware/periféricos:
```protobuf
service CompilationService {
  rpc CompileModel(CompileModelRequest) returns (CompileModelResponse);
  rpc GetCompilationStatus(GetCompilationStatusRequest) returns (CompileModelResponse);
  rpc TrainModel(TrainModelRequest) returns (TrainModelResponse);
  rpc GetSupportedHardware(GetSupportedHardwareRequest) returns (GetSupportedHardwareResponse);
  rpc GetSupportedSensors(GetSupportedSensorsRequest) returns (GetSupportedSensorsResponse);
  rpc GetSupportedActuators(GetSupportedActuatorsRequest) returns (GetSupportedActuatorsResponse);
}
```

#### Arquitectura del Worker Asíncrono (`app/worker.py`)
El servicio no ejecuta compilaciones dentro del ciclo del servidor gRPC. En su lugar, el servidor gRPC actúa como productor encolando trabajos en Redis, y el proceso `arq` actúa como consumidor.

1. **`CompileModel` / `TrainModel`**:
   * Encolan en el pool de Redis el trabajo correspondiente (`compile_job` o `train_job`).
   * Para evitar duplicados de trabajos idénticos pendientes de procesamiento en Redis, se calcula una clave de idempotencia (`_job_id="train:{model_id}"` o `_job_id="compile:{model_id}"`).

2. **Funcionamiento detallado de `train_job`**:
   * **Descarga de Dataset**: Utiliza el SDK de MinIO para descargar el zip del dataset desde el bucket `datasets` mediante su `dataset_key`.
   * **Ejecución del Subproceso**: Lanza un script independiente en Python (`app.compilers.yolo_train`) con los parámetros correspondientes (`--epochs`, `--gpu_percent`, etc.).
   * **Cancelación activa**: Lanza una corutina en segundo plano (`check_cancellation`) que monitoriza si existe la clave `cancel:train:{model_id}` en Redis. En caso positivo, finaliza el proceso de entrenamiento del sistema (`process.terminate()`) de forma inmediata.
   * **Streaming de logs**: Captura la salida estándar (`stdout`) del subproceso línea a línea, la publica en el canal de PubSub `train_logs:{model_id}` y la almacena en una lista de Redis `train_logs:{model_id}_list` para persistir el histórico (con un límite de 5000 líneas y expiración de 24 horas).
   * **Subida de Pesos**: Al finalizar correctamente, extrae el archivo `/run/<name>/weights/best.pt`, calcula su hash SHA-256 y lo sube al bucket `models` bajo la ruta `{model_id}/model.pt`.
   * **Notificación**: Realiza una llamada gRPC a `registry-service:50051` actualizando el estado a `"pending"`.

3. **Funcionamiento detallado de `compile_job`**:
   * **Resolución del Compilador**: Obtiene el objeto compilador correspondiente a la arquitectura destino (`hardware_type`) mediante el registro dinámico.
   * **Ejecución del compilador**: Invoca el método `compile()` del compilador físico (e.g. `HailoCompiler` o `AICamCompiler`).
   * **Notificación Final**: Actualiza el estado del modelo en `registry-service:50051` a `"ready"` (y guarda el `compiled_key` y el hash) o `"failed"` (y guarda el error). Adicionalmente, escribe en Redis en la clave `model_compile_done:{model_id}` el valor final para que otros servicios que esperan la compilación reciban la señal.

---

### 1.4. Edge Connector Service (`edge-connector-service`)

* **Directorio principal**: `services/edge-connector-service/`
* **Tecnología**: gRPC Server, arq Redis-based Task Queue, MQTT Client (`aiomqtt`), MongoDB Driver (`motor`), Prometheus Client.
* **Puertos**: `50053` (gRPC), `9100` (Prometheus metrics)

#### Interfaz gRPC
Hosts simultáneamente dos interfaces gRPC en el puerto `50053`:
* **`DeploymentService`** (`grpc_handlers/deployment_handler.py`)
* **`MonitoringService`** (`grpc_handlers/monitoring_handler.py`)

#### Unificación del Loop MQTT (`app/mqtt/listener.py`)
Un único cliente MQTT asíncrono gestiona todas las suscripciones a los dispositivos de campo, optimizando el ancho de banda y sockets:
1. **Telemetría (`device/{device_id}/telemetry`)**:
   * Escribe el último estado del dispositivo en MongoDB (`device_states`).
   * **Historial de telemetría**: Añade un log append-only en la colección `telemetry_history` para permitir auditoría temporal del consumo del hardware.
   * Actualiza las métricas Prometheus `aura_device_cpu_percent`, `aura_device_ram_percent` y `aura_device_ram_used_mb`.
   * **Sincronización OTA de librerías**: Compara el hash del dispositivo con el local del servidor. Si difieren, empaqueta la carpeta de periféricos `/app/hardware` en un ZIP in-memory, lo sube a MinIO y publica el comando `update_libraries` en MQTT.
2. **Resultados de Inferencia (`device/{device_id}/inference`)**:
   * Guarda las predicciones en MongoDB (`inference_results`) ordenadas por timestamp.
3. **Eventos de Despliegue (`device/{device_id}/events`)**:
   * Al recibir `deploy_ack`, actualiza el estado del despliegue en PostgreSQL a `"running"`.
   * Al recibir `deploy_failed`, actualiza el estado a `"failed"` guardando el error.

#### Orquestación Asíncrona (`worker.py`)
* El proceso worker arq ejecuta `compile_and_deploy_job` para despliegues condicionales.
* Lanza la compilación llamando a `mlops-service:50052` y monitorea de forma no bloqueante a Redis en la clave `model_compile_done:{model_id}`.
* Al finalizar con éxito, genera URLs firmadas y publica por MQTT el comando `deploy` al topic `device/{device_id}/commands`.

---

## 2. Bases de Datos de la Plataforma

Para garantizar coherencia, rendimiento y escalabilidad, la arquitectura utiliza tres tipos de almacenamiento:

### 2.1. PostgreSQL (Base de Datos Relacional)
* **Objetivo**: Persistencia transaccional de metadatos y configuraciones (Dispositivos, Modelos, Datasets, Scripts, Despliegues).
* **Servicio principal**: `postgres` (Base de datos relacional común).

### 2.2. MongoDB (Base de Datos Documental)
* **Objetivo**: Ingesta de alta frecuencia de telemetrías e inferencias en series temporales.
* **Colecciones**:
  * `device_states`: Último estado conocido de cada nodo.
  * `inference_results`: Registro persistente de predicciones neurales.
  * `telemetry_history`: Histórico append-only del consumo de recursos locales (CPU, memoria).

### 2.3. Redis (Almacenamiento en Memoria y Colas)
* **Objetivo**: Coordinación y colas asíncronas (`mlops_queue` y `deployment_queue`), logs PubSub de entrenamiento y flags de cancelación en tiempo real.

---

## 3. Flujo Completo de un Despliegue con Compilación Automática

```
Usuario      API Gateway    Registry Svc    Edge Connector    MLOps Service    Redis       Edge Device
  │               │              │                │                 │            │              │
  │── POST Deploy ─►              │                │                 │            │              │
  │               │── gRPC ─────►│                │                 │            │              │
  │               │   (Pending)  │                │                 │            │              │
  │               │              │── Job Enqueue ─►                │            │              │
  │               │              │   (arq Queue)  │                 │            │              │
  │               │              │                │── gRPC ────────►│            │              │
  │               │              │                │   CompileModel  │            │              │
  │               │              │                │                 │── Job ────►│              │
  │               │              │                │                 │   (arq)    │              │
  │               │              │                │                 │            │              │
  │               │              │                │                 │ [Worker]   │              │
  │               │              │                │                 │ Compila y  │              │
  │               │              │                │                 │ sube a     │              │
  │               │              │                │                 │ MinIO      │              │
  │               │              │                │                 │            │              │
  │               │              │                │   Updates Redis ◄────────────│              │
  │               │              │                │   done_status   │            │              │
  │               │              │                │                 │            │              │
  │               │              │                │◄── Polls Redis ─┼────────────│              │
  │               │              │                │   (ready)       │            │              │
  │               │              │                │                 │            │              │
  │               │              │                │── Publish command (MQTT) ────┼─────────────►│
  │               │              │                │   "deploy"                   │              │
  │               │              │                │                              │              │
  │               │              │                │◄───────────────── Event deploy_ack (MQTT) ──│
  │               │              │                │                                             │
  │               │              │                │── Updates Postgres DB (status = running) ──►│
```

---

## 4. Cómo Inicializar un Dispositivo IoT

### Paso 1: Configurar la Identidad y Conexión (`device_config.yaml`)
El dispositivo Edge requiere un identificador único y los parámetros del broker MQTT. Esta información se establece en el fichero [device_config.yaml](file:///c:/Users/Estela/TFM_MIoT/edge-runtime/config/device_config.yaml):

```yaml
device_id: dev-device-001
mqtt_host: broker.aura-platform.local
mqtt_port: 1883
mqtt_reconnect_interval_s: 5
hardware_type: rpi
telemetry_interval_s: 10
inference_interval_s: 0.1
work_dir: /tmp/aura
config_dir: /app/config
log_level: INFO
```

### Paso 2: Declarar Componentes y Periféricos Físicos (`components_config.yaml`)
En el archivo [components_config.yaml](file:///c:/Users/Estela/TFM_MIoT/edge-runtime/config/components_config.yaml), registre todos los sensores y actuadores físicos conectados:

```yaml
components:
  - id: camera_0
    type: camera
    driver: opencv
    enabled: true
    params:
      source: 0
      resolution: [640, 480]
      fps: 10

  - id: env_sensor_0
    type: sensor
    driver: bme280
    enabled: true
    params:
      bus: 1
      address: "0x76"
      measurements: [temperature, humidity]
```

### Paso 3: Lanzar el Agente
Al arrancar el script de entrada `agent.py`:
1. El **`DeviceManager`** lee la configuración de componentes e inicializa el hardware local llamando al método `initialize()`.
2. Se conecta al Broker MQTT e inicia la suscripción al canal `device/{device_id}/commands`.
3. Levanta el bucle de inferencia y telemetría de forma asíncrona coordinados por `asyncio.TaskGroup`.

---

## 5. Flujo de Registro de Recursos (Modelos, Datasets y Scripts)

El registro de recursos en la plataforma AURA permite catalogar y preparar los artefactos necesarios para la inferencia y el entrenamiento en los dispositivos edge. El flujo principal se detalla a continuación tomando como ejemplo el registro de un modelo de IA (`.pt`):

1. **Subida y Metadatos**: El operador utiliza el Frontend (Next.js) para seleccionar el fichero del modelo `.pt` e introducir la descripción y otros metadatos.
2. **Carga en MinIO**: El API Gateway recibe el fichero de modelo mediante una petición HTTP POST multiparte y lo sube directamente al bucket `models` de MinIO bajo la ruta `models/{id}/model.pt`.
3. **Registro en Base de Datos**: Tras confirmar la subida, el API Gateway realiza una llamada gRPC `RegisterModel` al Registry Service (`registry-service` puerto `50051`), el cual inserta los metadatos e identificadores de MinIO en la base de datos PostgreSQL en la tabla `models` con el estado inicial `"pending"`.
4. **Respuesta**: El Registry Service responde al API Gateway y este devuelve un código HTTP `201 Created` al Frontend.

### Registro Análogo de Datasets y Scripts
El registro de datasets y de scripts de post-procesamiento se realiza de forma completamente **análoga**:
* **Datasets**: Se sube un archivo comprimido `.zip` a MinIO (bucket `datasets`), y se guardan sus metadatos (tamaño, hash SHA-256) en PostgreSQL (`datasets` table) a través del Registry Service.
* **Scripts**: El script de Python `.py` se valida estáticamente (mediante AST para comprobar la firma y evitar librerías no permitidas), se sube a MinIO (bucket `scripts`) y sus metadatos se guardan en PostgreSQL (`scripts` table) a través de `ScriptService`.

---

## 6. Flujo Conceptual de Reentrenamiento de Modelos

> [!NOTE]
> El flujo de reentrenamiento de modelos detallado a continuación es una **especificación conceptual** del ciclo de vida de MLOps en AURA. Actualmente, el proyecto no implementa físicamente el auto-reentrenamiento por deriva en la base de código del PoC, pero está diseñado para soportarlo siguiendo este flujo:

1. **Disparador del Reentrenamiento (Trigger)**:
   * **Manual**: Un operador decide reentrenar un modelo desde la interfaz de usuario seleccionando un nuevo dataset y ajustando hiperparámetros.
   * **Automático (Detección de Deriva/Drift)**: El detector de deriva del API Gateway o un servicio externo de monitorización observa que la precisión del modelo en producción o la confianza media de las predicciones baja de un umbral establecido (analizando los datos en MongoDB `inference_results`).
2. **Generación del Nuevo Registro**: El API Gateway invoca al Registry Service mediante gRPC (`CreateRetrainedModel`) para crear un nuevo registro de modelo con un enlace al modelo padre (`parent_id`) en PostgreSQL, marcando su estado como `"training"`.
3. **Encolado en la Cola de MLOps**: Se envía una llamada gRPC `TriggerRetraining` al MLOps Service (puerto `50052`), el cual calcula una clave de idempotencia y encola la tarea `train_job` en la cola Redis `mlops_queue`.
4. **Procesamiento Asíncrono (arq worker)**:
   * El worker de MLOps descarga los pesos del modelo padre desde MinIO (`models/{parent_id}/model.pt`) para utilizarlos como pesos iniciales (transfer learning/fine-tuning).
   * Descarga el nuevo dataset ZIP desde MinIO.
   * Ejecuta el script de entrenamiento de YOLO pasando los pesos del modelo padre como base.
   * Los logs de entrenamiento se transmiten en tiempo real a Redis PubSub y se guardan en la lista Redis para que el frontend los renderice.
   * Tras la finalización exitosa, se suben los nuevos pesos resultantes (`best.pt`) a MinIO bajo `models/{new_model_id}/model.pt`.
   * Se notifica al Registry Service vía gRPC, actualizando el estado del nuevo modelo a `"pending"` (listo para compilar).

