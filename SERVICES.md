# API-Gateway

El api-gateway es la puerta de entrada HTTP de toda la plataforma. El frontend no habla directamente con los microservicios gRPC; llama al gateway, y este decide a qué servicio reenviar cada operación. Eso se ve en main.py:1, donde se crea la app FastAPI, se configura CORS para localhost:3000 y localhost:3001, y se registran los routers de devices, models, scripts, deployments y monitoring.

La parte de login es simple: el endpoint /auth/token compara usuario y contraseña contra un usuario demo hardcodeado en jwt.py:1. Ahora mismo ese usuario es admin / aura2026. Si coincide, el gateway genera un JWT con create_token(); si no, devuelve 401 Invalid credentials. Ese token luego se usa en el frontend como Bearer para acceder al resto de endpoints.

Después del login, casi todas las rutas protegidas usan verify_token() de jwt.py:1 como dependencia. Es decir, el gateway valida el JWT antes de proxyar la petición. Los routers, por ejemplo devices.py:1 y monitoring.py:1, reciben la petición ya autenticada y llaman al stub gRPC correspondiente con get_stub(...).

La configuración vive en config.py:1. Ahí están los hosts y puertos de los servicios gRPC, el secreto JWT y los parámetros de MinIO. El gateway también inicializa MinIO en el arranque porque maneja subidas de ficheros directamente, para no pasar binarios grandes por gRPC.

En resumen: frontend → gateway HTTP → validación JWT → proxy a microservicios gRPC.

Flujo general
El frontend llama a api.ts con Axios. Esa capa apunta al api-gateway, y el gateway valida el JWT antes de reenviar la petición al servicio real. El login vive en main.py:1 y el token se crea en jwt.py:1.

Endpoints principales

POST /auth/token desde frontend/app/(auth)/login/page.tsx/login/page.tsx#L1) → main.py:1 → devuelve JWT.
GET /api/devices, POST /api/devices, DELETE /api/devices/:id → devices.py:1 → servicio device-service.
GET /api/models, POST /api/models, DELETE /api/models/:id → router de models del gateway → ai-service y compilation-service.
GET /api/scripts, POST /api/scripts, DELETE /api/scripts/:id → router de scripts del gateway → script-service.
GET /api/deployments, POST /api/deployments → router de deployments del gateway → deployment-service.
GET /api/monitoring/devices, GET /api/monitoring/devices/:id, GET /api/monitoring/devices/:id/inference → monitoring.py:1 → monitoring-service.

Cómo se protege
Todas las rutas bajo /api/* usan verify_token() de jwt.py:1. O sea: si no hay Bearer token, el gateway corta la petición antes de hablar con los servicios.

# Device Service

Qué hace el device-service

Propósito: Gestiona el inventario de dispositivos (CRUD) y su estado (online/offline, last_seen). Expone un servicio gRPC que el resto del sistema usa para crear/listar/borrar dispositivos y actualizar su estatus. Ver arranque en main.py:1-40.
Responsabilidades principales:

CreateDevice: crear un nuevo dispositivo en la BD.
GetDevice: recuperar metadatos de un dispositivo.
ListDevices: listar todos los dispositivos.
DeleteDevice: eliminar un registro de dispositivo.
UpdateDeviceStatus: actualizar status y last_seen_at (p. ej. cuando el edge se conecta o envía heartbeat). Implementaciones en DeviceServiceHandler en device_handler.py:1-120.
Modelo de datos (Postgres / ORM):

Tabla devices (Device): campos principales:
id (UUID), name, hardware_type, description
status (por defecto "offline")
last_seen_at, created_at
Definición en orm.py:1-120.
Repositorio y operaciones DB:

DeviceRepository encapsula las operaciones: create, get, list_all, update_status, delete. Actualiza timestamps y persiste cambios. Ver devices.py:1-120.
Interacciones con otros servicios y el sistema:

API Gateway / Frontend: el api-gateway hará llamadas al stub gRPC del device-service para exponer endpoints HTTP al frontend (create/list devices desde la UI).
Deployment / Monitoring / Otros: otros servicios (por ejemplo deployment-service) consultan la existencia y estado de devices a través de este servicio (p. ej. DeploymentService valida que device_id exista antes de crear un deployment).
MQTT: el device-service no publica ni suscribe directamente a MQTT (esa responsabilidad recae en monitoring-service y deployment-service para eventos y comandos), pero sí mantiene el estado que se sincroniza cuando otros componentes reciben eventos MQTT y llaman a UpdateDeviceStatus.
Comportamiento operativo y consideraciones:

Status updates: update_status marca last_seen_at y cambia status (útil para heartbeats). Asegúrate de cómo y cuándo los agents llaman a esto (directamente o vía monitoring-service).
Consistencia: el servicio no maneja colas ni reintentos por sí mismo — operaciones son transaccionales en Postgres.
Seguridad: no hay lógica de autenticación aquí; se asume que el api-gateway controla acceso y autentica antes de invocar estas RPCs.
Escalabilidad: es un servicio ligero (solo CRUD + DB); escala según necesidades de conexión gRPC/DB.

## Generación de librerías de AURA para sensores, actuadores, nodos y arquitecturas.

# AI-Service

AI-service es el servicio que lleva el catálogo de modelos y sus artefactos. No recibe peticiones directas del frontend; el flujo normal es frontend → api-gateway → ai-service. Lo puedes ver en models.py:1, donde el gateway llama al stub gRPC de AI-service.

Su entrada está en main.py:1. Al arrancar hace tres cosas importantes: crea las tablas del modelo en PostgreSQL, inicializa MinIO para guardar ficheros y levanta un servidor gRPC en el puerto 50052. O sea, AI-service es básicamente el backend de persistencia y metadatos para los modelos.

Lo que guarda de cada modelo está definido en orm.py:1. Ahí se ve que un modelo tiene nombre, descripción, la key del fichero original en MinIO, su SHA256, y después campos para el artefacto compilado, el tipo de hardware y el estado de compilación. El repositorio de acceso a datos en models.py:1 hace las operaciones CRUD y también actualiza el resultado de la compilación.

El contrato gRPC está en ai.proto:1. AI-service expone cinco operaciones: subir modelo, obtenerlo, listar, borrar y actualizar el estado de compilación. El handler real está en ai_handler.py:1: traduce las llamadas gRPC a operaciones sobre PostgreSQL y devuelve siempre la representación del modelo.

La parte de compilación se coordina desde el servicio de compilación, no desde AI-service. En compilation_handler.py:1 se ve que, cuando se lanza una compilación, primero marca el modelo como compilando en AI-service, luego compila en background, y al terminar vuelve a llamar a AI-service para dejar el estado en ready o failed.

En una frase: AI-service es el registro central de modelos. Guarda metadatos, controla el estado de compilación y sirve de fuente de verdad para el resto de la plataforma.

## Falta añadir training y retraining, pero la idea es que AI-service también gestione las versiones de modelos y sus métricas de entrenamiento. Por ahora es solo un catálogo de artefactos, pero la arquitectura ya está pensada para evolucionar hacia un MLOps más completo. Tmb en retraining, que pueda ser manual, x tiempo o x suceso.

## Falta poder subir datasets a AURA, que además se necesitan para la compilación. La idea tmb es que AI-service también pueda gestionar datasets y sus versiones, para tener todo el ciclo de vida del ML centralizado. Además, en los modelos subidos se puede asociar el dataset correspondiente y viceversa.

# Script-Service

script-service es el servicio que gestiona los scripts de inferencia de la plataforma. No ejecuta los scripts; los registra, los lista, los borra y guarda su metadato en PostgreSQL mientras el fichero real se almacena en MinIO. La entrada del servicio está en main.py:1, donde arranca el gRPC en el puerto 50053, crea las tablas de scripts y configura el bucket de MinIO llamado scripts.

El flujo real es este: el frontend sube un fichero .py al gateway, el gateway lo manda primero a MinIO y luego llama al script-service con la key y el SHA256 del archivo. Eso se ve en scripts.py:1. El servicio no recibe el binario completo; recibe solo metadata y referencias al objeto guardado.

Lo que guarda cada script está definido en orm.py:1. Un script tiene nombre, descripción, hardware_type, script_key, script_sha256 y fecha de creación. El repositorio en scripts.py:1 hace las operaciones CRUD sobre esa tabla.

El contrato gRPC está en script.proto:1. Expone cuatro operaciones: subir, obtener, listar y borrar scripts. El handler real está en script_handler.py:1: traduce cada llamada gRPC a una operación de base de datos y devuelve la respuesta normalizada.

En una frase: script-service es el catálogo de scripts de inferencia. El gateway sube el fichero a MinIO, script-service guarda la referencia y el resto del stack usa esa metadata cuando despliega modelos en dispositivos.

## Falta que compruebe el contenido del script para evitar que suban código malicioso. Por ahora el servicio asume que los scripts son confiables, pero en producción habría que añadir validación de seguridad, como análisis estático o sandboxing.

## Falta añadir versiones de scripts, pero la idea es que script-service también gestione versiones y dependencias entre scripts, para facilitar el mantenimiento. Por ahora es un catálogo plano, pero la arquitectura ya está pensada para evolucionar hacia un MLOps más completo.

## Falta añadir que se puedan escribir en el IDE y las librerias propias de AURA. Por ahora solo se pueden subir como archivos .py, pero la idea es que en el futuro se pueda escribir directamente en el frontend con autocompletado y validación, para mejorar la experiencia de usuario.

# Compilation-Service

compilation-service es el servicio que toma un modelo ya subido y lo convierte al formato de hardware objetivo. No compila desde el frontend directamente: el flujo normal es frontend → models.py:1 → main.py:1. El gateway sube primero el .pt a MinIO, registra el modelo en ai-service, y luego dispara la compilación si compile=true.

La entrada del servicio está en main.py:1. Ahí arranca un gRPC server en el puerto 50054 y crea un CompilationServiceHandler. Ese handler es el que decide qué compilador usar según hardware_type, mediante un registro interno en compilation_handler.py:1.

El contrato gRPC está en compilation.proto:1. Solo expone dos operaciones:

CompileModel
GetCompilationStatus
La idea es esta: CompileModel responde enseguida con status="compiling" y deja la tarea corriendo en segundo plano. Después puedes consultar el estado con GetCompilationStatus, que en realidad delega en ai-service para leer el estado actualizado del modelo.

Lo importante del flujo interno está en compilation_handler.py:1:

Si el hardware no tiene compilador, marca el modelo como failed en ai-service.
Si sí hay compilador, marca primero compiling.
Lanza la compilación como tarea asyncio en background.
Cuando termina, vuelve a notificar a ai-service con ready o failed.
Los compiladores reales están en hailo.py:1 y aicam.py:1. Hoy hay dos rutas implementadas:

hailo8 y hailo8l usan HailoCompiler
rpi_ai_cam usa AICamCompiler
Y hay dos pendientes, comentadas en el código:

rpi
jetson_orin_nano
El proceso general es: descargar el .pt desde MinIO, compilarlo para el hardware objetivo, subir el artefacto compilado a MinIO y devolver un CompilationResult con la key y el hash. La base común de esa interfaz está en base.py:1.

En resumen: compilation-service no guarda modelos ni scripts; orquesta la transformación del modelo para un hardware concreto y publica el resultado. ai-service guarda el estado, y compilation-service hace el trabajo pesado.

## Falta hacer que compilation sea en deployment si no está compilado ya. No se ejecuta cuando se añade el modelo. Se ejecuta cuando se despliega en un hardware específico.

# Deployment-Service

Qué hace:

Propósito: Orquestrar despliegues de modelos y scripts a dispositivos edge. Crea registros de despliegue, envía el comando de despliegue al dispositivo vía MQTT y actualiza el estado según los eventos que publique el dispositivo.
Arranque: Inicia un servidor gRPC (añade el servicer DeploymentService) y lanza un listener MQTT en background. Ver en main.py:1-40.
Flujo principal (CreateDeployment):

Validaciones: comprueba que exista device, model y script y que el model esté compilado (estatus "ready"). Código en deployment_handler.py:1-120.
Creación: crea un registro de despliegue en la BD con DeploymentRepository.create. Repositorio en deployments.py:1-60.
Presigned URLs: genera URLs presignadas para descargar el artefacto compilado y el script desde MinIO (shared.utils.minio.presigned_url).
Comando MQTT: publica en el topic device/{device_id}/commands un JSON con:
command: "deploy"
deployment_id
model_url, model_sha256
script_url, script_sha256
(publicación con aiomqtt; si falla, marca el despliegue como failed y aborta el RPC). Implementación en deployment_handler.py:30-120.
Marcado: si la publicación se envía, marca el despliegue como sent (mark_sent); el listener MQTT se encargará de marcar running/failed cuando el edge confirme.
Eventos y actualización de estado (listener MQTT):

Subscripción: DeploymentEventListener se suscribe a device/+/events y procesa mensajes de dispositivos. Ver en listener.py:1-80.
Eventos esperados:
deploy_ack → marca deployment como running (mark_running).
deploy_failed → marca deployment como failed (mark_failed) y guarda el mensaje de error.
Formato: el listener espera payload JSON con campos event y deployment_id.
API gRPC exposada:

CreateDeployment — crea y envía el despliegue (explicado arriba).
GetDeployment — recupera un despliegue por id.
ListDeployments — lista todos los despliegues.
ListDeviceDeployments — lista despliegues de un dispositivo.
(Implementaciones en deployment_handler.py.)
Dependencias e integraciones externas:

MinIO: para almacenar/servir artefactos compilados y scripts (presigned URLs). Inicializado en main.py.
Postgres: almacena la tabla Deployment, referencias a Device/Model/Script. ORM en orm.py.
MQTT broker (mosquitto): medio para enviar comandos a dispositivos y recibir ack/fail. Host/puerto provistos por la configuración.
API Gateway / Frontend: la UI solicita un despliegue al api-gateway, que invoca el stub gRPC del deployment-service. (El gateway traduce HTTP→gRPC).
Otros servicios: no se hacen llamadas gRPC a ai/script/compilation desde aquí; el servicio asume que las referencias a modelo/script están en la BD y que los artefactos compilados están en MinIO (gestionados por ai-service / compilation-service / script-service).
Puntos clave y recomendaciones:

Idempotencia/estado: el servicio crea un registro antes de enviar el comando y luego marca estados; revisar si hace falta protección contra re-envíos duplicados desde UI.
Seguridad de presigned URLs: las URLs pueden expirar; asegurarse de expiraciones coherentes con tiempo de descarga en edge.
Visibilidad/telemetría: los logs ya informan envíos y errores; considera publicar eventos de auditoría si necesitas trazabilidad centralizada.
Manejo de errores MQTT: hoy marca failed si la publicación falla; si el broker está temporalmente inaccesible, quizá sea útil reintentar con backoff antes de fallar definitivamente.
Pruebas: para probar E2E en local:
subir modelo/script y marcar compilado ready en la BD (o usar ai-service + compilation flow),
llamar CreateDeployment (por gRPC o vía API Gateway),
simular el agent: suscribirse a device/{id}/commands, descargar los URLs, y publicar device/{id}/events con deploy_ack o deploy_failed.

## Falta cambiar que la compilación se haga aquí si no está compilado.
## Falta añadir que se pueda desplegar manual, en x tiempo o con x suceso. Por ahora solo se puede desplegar inmediatamente, pero la idea es que en el futuro se puedan programar despliegues o hacerlos condicionales según métricas.

# Monitoring-Service

Qué hace (resumen):

Recoge telemetría e inferencia publicada por dispositivos edge vía MQTT, almacena estado actual y resultados de inferencia en MongoDB, y expone un servicio gRPC para leer ese estado desde la UI/otros servicios. Además exporta métricas Prometheus. Arranca en main.py:1-40.
Entradas (MQTT):

device/{device_id}/telemetry → payload JSON con campos como cpu_percent, ram_percent, ram_used_mb, active_model_id, active_script_id, active_deployment_id. Procesado en listener.py:1-120.
Acción: upsert en device_states (marca status: online, actualiza last_seen_at) y actualización de métricas Prometheus (aura_device_cpu_percent, aura_device_ram_percent, aura_device_ram_used_mb).
device/{device_id}/inference → payload JSON con deployment_id y result_json. Acción: insertar documento en inference_results.
Almacenamiento (MongoDB):

Colecciones usadas (constantes): device_states y inference_results. Ver mongo.py:1-40.
device_states: documento upsert por device_id con estado actual y last_seen_at.
inference_results: insert append-only con timestamp y result_json.
API gRPC que expone: (handler en monitoring_handler.py:1-200)

GetDeviceState(device_id) → devuelve último estado (o NOT_FOUND).
ListDeviceStates() → devuelve estados de todos los devices.
GetInferenceResults(device_id, limit) → devuelve últimos resultados de inferencia (ordenados por timestamp desc).
Internamente usa MonitoringRepository (Mongo wrapper) en monitoring.py:1-200.
Métricas / observabilidad:

Exporta métricas Prometheus en el puerto configurado (inicio en main.py con start_http_server).
Tres Gauges por device: aura_device_cpu_percent, aura_device_ram_percent, aura_device_ram_used_mb (definidos en el listener).
Dependencias y arranque:

Conecta a MongoDB (motor.motor_asyncio.AsyncIOMotorClient) y crea un repo_factory que devuelve MonitoringRepository.
Lanza servidor gRPC (p. ej. puerto 50056) y un listener MQTT en background. Ver main.py:1-40.
Consideraciones operativas y recomendaciones:

TTL en inference_results puede ser útil si no quieres que la colección crezca indefinidamente (añadir índice TTL en Mongo si procede).
Prometheus: ajustar cardinalidad de etiquetas (aquí label= device_id) según número máximo de devices para evitar explosion de series.
Backpressure / rendimiento: si hay muchos mensajes, Motor + Mongo pueden necesitar tuning y/o un buffer/cola entre MQTT y escritura.
Validación de payloads: listener usa .get(...) y no valida tipos fuertemente; podría añadirse validación/transformación para evitar datos inválidos.
Relación con device-service: device_states es independiente; sin embargo, puedes mantener sincronización (p. ej. crear device en device-service cuando se vea por primera vez en monitoring) si lo quieres.

## Falta añadir coordenadas GPS en la telemetría, para poder mostrar la ubicación de los dispositivos en un mapa en el frontend. Por ahora solo se recoge CPU/RAM, pero la idea es que en el futuro se puedan añadir más métricas y datos contextuales.




El entrenamiento y la compilación se ejecutan en el compilation-service y no en el ai-service por razones de diseño arquitectónico y de gestión de recursos:

Aislamiento de Recursos (CPU/GPU) y Escalabilidad: El entrenamiento (PyTorch/YOLO) y la compilación (MCT, TensorRT, Hailo Compiler) son operaciones extremadamente pesadas. Si se ejecutaran en el ai-service, este podría quedarse sin memoria (OOM), consumir toda la CPU/GPU y congelar el API Gateway y el resto de la plataforma. Al separarlo en compilation-service, este servicio funciona como un worker asíncrono (utilizando Redis y arq) con colas de ejecución. El ai-service sigue siendo ligero y responde instantáneamente a las peticiones del usuario.

Acceso a Hardware Específico (GPU/CUDA): Solo el compilation-service necesita estar desplegado con acceso directo a la tarjeta gráfica NVIDIA (usando nvidia-container-toolkit) y montar sockets como /var/run/docker.sock para levantar los compiladores de hardware en contenedores. El ai-service no requiere controladores CUDA ni hardware dedicado, por lo que puede escalar horizontalmente en cualquier máquina convencional.

Independencia de Dependencias: El compilation-service contiene dependencias de gran volumen como torch, torchvision y compiladores específicos de hardware, haciendo que su imagen Docker sea muy grande. Mantener el ai-service libre de estas dependencias simplifica su mantenimiento y agiliza sus despliegues.

5:40 PM
Que es lo que hace ai-service y que es lo que hace compilation-service?
5:41 PM
Aquí tienes el detalle de responsabilidades de cada servicio dentro de la arquitectura de la plataforma:

AI Service (ai-service)
Es el servicio encargado de la gestión de datos, metadatos y el estado de los modelos y datasets de Inteligencia Artificial. Actúa como el cerebro administrativo:

CRUD de Modelos y Datasets: Registra en la base de datos relacional (PostgreSQL) la información de todos los modelos (nombre, descripción, arquitectura base, épocas, tamaño de entrada) y de los conjuntos de datos subidos.
Estado del Ciclo de Vida: Controla el estado del modelo (pending, training, ready, failed).
Asociaciones: Gestiona la relación de qué dataset pertenece a qué modelo para ser utilizado en el entrenamiento.
API de Metadatos: Proporciona los stubs gRPC para que el api-gateway y otros servicios consulten qué modelos están disponibles.
Compilation Service (compilation-service)
Es el servicio encargado de la ejecución física y de cómputo pesado. Funciona de forma asíncrona mediante trabajadores (workers) y una cola de Redis:

Entrenamiento de Modelos (YOLO):
Descarga el dataset empaquetado (.zip) desde el almacenamiento (MinIO).
Extrae las imágenes y etiquetas.
Ejecuta el script yolo_train.py en un subproceso del sistema.
Transmite los logs de entrenamiento en tiempo real a Redis para que los puedas ver en el frontend.
Sube el modelo resultante (best.pt) de vuelta a MinIO.
Compilación a Hardware Edge:
Adapta y optimiza los modelos (.pt) a formatos nativos de dispositivos específicos mediante compiladores:
Hailo8/8L: Convierte a formato .hef.
Raspberry Pi AI Cam (IMX500): Exporta a formato .imx (empaquetado con metadatos).
Jetson Orin Nano: Compila a TensorRT .engine.
Raspberry Pi Convencional: Exporta a TensorFlow Lite .tflite.
Notificaciones: Al terminar o fallar un entrenamiento/compilación, llama por gRPC al ai-service para actualizar el estado del modelo en la base de datos.
Rebuild container finished
I will wait for docker compose up -d to finish building and starting all the services.

docker compose up finished
I will wait for the verification command to complete.

Verify imports in container finished
I will wait for the uninstall to finish.

Uninstall package finished
I will wait for the verification command to complete.

Verify imports again finished
I will wait for the force reinstall to complete.

Reinstall package finished
I have successfully implemented all fixes and verified the changes!

Summary of Fixes
Dataset Upload Status (pending -> no file -> ready):

Root Cause: When you close the file upload picker, the browser window gains focus, which triggers a React Query refetch for the datasets. Since the database record is created immediately by UploadDataset but the file bytes take a few seconds to upload to MinIO before SetDatasetFile updates the record, the database transiently had a record with object_key = null. This caused the refetched list to display no file.
Fix: In 

page.tsx
, we modified the list mapping logic. If there is an active upload in progress for a dataset name and the server returns the record with object_key = null, we maintain its UI status as pending (and keep action buttons disabled) until the upload request finishes and the final invalidation updates the status to ready.
YOLO Training Dependency (ImportError):

Root Cause: The slim Python base image of the compilation container lacks the GUI (X11/XCB) system dependencies required by standard opencv-python. When ultralytics attempted to import cv2, it crashed with ImportError: libxcb.so.1: cannot open shared object file.
Fix: Added opencv-python-headless>=4.8.0 to 

requirements.txt
 before ultralytics, satisfying the OpenCV dependency without requiring GUI libraries. We rebuilt the container and verified that import ultralytics now loads successfully inside the compilation-service container.
Bonus: Improved the ImportError blocks in both the 

compilation compiler
 and 

local script
 to print the actual traceback, preventing library import issues from being silently masked in the future.
You can view the full details of the implementation and test verification in the 
walkthrough.md
.