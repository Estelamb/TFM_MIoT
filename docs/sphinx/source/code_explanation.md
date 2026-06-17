# Explicación del Código por Carpetas y Archivos

Esta sección proporciona una radiografía detallada de la base de código de **AURA Platform**. Aquí se detalla la función de cada directorio, módulo y archivo clave para guiar a los desarrolladores a través del proyecto.

---

## Estructura General del Proyecto

El repositorio está organizado como una arquitectura de microservicios con un runtime de edge independiente en Python, compartiendo código común a través de una carpeta compartida (`shared`).

```
TFM_MIoT/
├── .env.example                # Plantilla de variables de entorno globales
├── docker-compose.yml          # Orquestación de contenedores del backend e infraestructura
├── README.md                   # Resumen del proyecto y comandos rápidos
├── RUNNING.md                  # Manual detallado de despliegue
├── data/                       # Volúmenes persistentes de bases de datos locales (ignorado en git)
├── docker/                     # Configuraciones y entrypoints específicos de Docker
├── docs/                       # Documentación del proyecto (Sphinx y TypeDoc)
├── services/                   # Microservicios del backend (gRPC/REST/MQTT)
├── edge-runtime/               # Agente Python que corre en el dispositivo físico
├── frontend/                   # Interfaz de usuario Next.js 15 (App Router)
├── shared/                     # Librerías comunes y stubs gRPC autogenerados
├── hardware/                   # Módulos físicos y utilidades de hardware
└── scripts/                    # Scripts de utilidad para desarrollo y tests
```

---

## 1. Servicios del Servidor (`services/`)

Contiene los microservicios que componen la infraestructura central. Se comunican internamente mediante **gRPC** y externamente a través del **API Gateway** mediante **HTTP REST**.

### `services/api-gateway/`
Centraliza los accesos de la interfaz web y valida las credenciales.
* [api-gateway/app/main.py](file:///c:/Users/Estela/TFM_MIoT/services/api-gateway/app/main.py): Inicializa la aplicación FastAPI, configura el middleware de CORS y monta los enrutadores REST.
* [api-gateway/app/config.py](file:///c:/Users/Estela/TFM_MIoT/services/api-gateway/app/config.py): Carga y valida las configuraciones del Gateway (JWT, host de gRPC, puertos).
* [api-gateway/app/stubs.py](file:///c:/Users/Estela/TFM_MIoT/services/api-gateway/app/stubs.py): Inicializa y cachea los canales de comunicación gRPC hacia los microservicios internos.
* **`app/auth/`**: Contiene la lógica para la gestión de tokens JWT y hashing de contraseñas.
* **`app/routers/`**: Enrutadores FastAPI individuales que mapean endpoints REST a llamadas gRPC:
  * `deployments.py`: Gestión del ciclo de vida de los despliegues (OTA).
  * `devices.py`: Registro, listado y estado de dispositivos edge.
  * `models.py`: Carga y gestión de archivos de modelos `.pt` y metadatos de optimización.
  * `scripts.py`: Gestión de scripts de inferencia en Python.
  * `monitoring.py`: Endpoint de telemetría y WebSocket para datos en vivo.

### `services/registry-service/`
Servicio de catálogo de datos de la plataforma. Gestiona la persistencia de dispositivos, modelos y scripts.
* [registry-service/app/main.py](file:///c:/Users/Estela/TFM_MIoT/services/registry-service/app/main.py): Levanta el servidor gRPC del servicio en el puerto `50051`.
* **`app/grpc_handlers/`**: Controladores que procesan las peticiones RPC entrantes de modelos, scripts y dispositivos.
* **`app/repositories/`**: Implementaciones del patrón Repository para interactuar con la base de datos PostgreSQL utilizando SQLAlchemy.
* **`app/models/`**: Esquemas de base de datos relacionales (declaración de tablas PostgreSQL mediante SQLAlchemy).

### `services/mlops-service/`
Gestiona la compilación de modelos de aprendizaje automático hacia formatos específicos de hardware.
* [mlops-service/app/main.py](file:///c:/Users/Estela/TFM_MIoT/services/mlops-service/app/main.py): Levanta el servidor gRPC del servicio en el puerto `50052`.
* [mlops-service/app/worker.py](file:///c:/Users/Estela/TFM_MIoT/services/mlops-service/app/worker.py): Ejecuta tareas asíncronas de compilación e interactúa con el socket de Docker para instanciar contenedores de compilación aislados.
* **`app/compilers/`**: Abstracciones de compilación para los diferentes backends (Hailo, TensorRT, TFLite).

### `services/edge-connector-service/`
El puente de comunicación entre la plataforma y los dispositivos perimetrales.
* [edge-connector-service/app/main.py](file:///c:/Users/Estela/TFM_MIoT/services/edge-connector-service/app/main.py): Inicializa el servidor gRPC en el puerto `50053`.
* [edge-connector-service/app/worker.py](file:///c:/Users/Estela/TFM_MIoT/services/edge-connector-service/app/worker.py): Escucha eventos procedentes del Broker MQTT (telemetría, logs de inferencia) y los persiste asíncronamente en MongoDB y Prometheus.
* **`app/mqtt/`**: Clientes de mensajería MQTT para subscripción a topics y publicación de comandos.

---

## 2. Runtime de Edge (`edge-runtime/`)

Código diseñado para ejecutarse localmente en el dispositivo de hardware (ej. Raspberry Pi 5).

* [edge-runtime/agent.py](file:///c:/Users/Estela/TFM_MIoT/edge-runtime/agent.py): El bucle principal del agente. Conecta al broker MQTT, reporta telemetría del sistema periódicamente y procesa las órdenes de despliegue entrantes (descarga de MinIO, validación de hashes, actualización del script de inferencia).
* **`edge-runtime/pal/`**: Capa de Abstracción de Plataforma (Platform Abstraction Layer):
  * `comm_client.py`: Maneja el socket MQTT cliente local y el ciclo de vida de la conexión física.
* **`edge-runtime/aura_hw/`**: El núcleo de abstracción del hardware local:
  * `detect.py`: Módulo que comprueba la presencia de aceleradores de hardware en el sistema operativo mediante llamadas a nivel de sistema.
  * `device_manager.py`: Inicializa e interactúa de manera directa con las cámaras de video e interfaces del dispositivo.
  * `loader.py`: Realiza la carga dinámica en memoria de los scripts Python de inferencia que el usuario subió remotamente a la plataforma.
  * `runtime.py`: Orquesta la inferencia llamando al backend detectado.
  * **`aura_hw/backends/`**: Contiene implementaciones de bajo nivel para las diferentes arquitecturas de aceleración (Hailo-8, IMX500, CPU/TFLite, Jetson Nano).

---

## 3. Interfaz de Usuario (`frontend/`)

Aplicación moderna e interactiva construida en **Next.js 15** (TypeScript + Tailwind CSS).

* **`frontend/app/`**: Estructura del Next.js App Router:
  * `layout.tsx` y `page.tsx`: Estructura principal y dashboard de bienvenida.
  * **`(app)/deployments/`**: Página de creación y monitorización de despliegues activos.
  * **`(app)/devices/`**: Vista de dispositivos registrados y su estado de conexión.
  * **`(app)/models/`**: Formulario de carga y visor de modelos.
  * **`(app)/scripts/`**: Repositorio de scripts de ejecución.
  * **`(app)/monitoring/`**: Dashboard gráfico que consume WebSockets para mostrar CPU, RAM y streams de inferencia en vivo.
* **`frontend/components/`**: Componentes UI altamente reutilizables (gráficas de telemetría, modales de formulario, tarjetas de estado, terminales de log).
* **`frontend/hooks/`**: React hooks personalizados para suscripciones a WebSockets y peticiones de datos de la API.
* **`frontend/lib/`**: Helpers y clientes HTTP de Axios para interactuar de forma tipada con el `api-gateway`.

---

## 4. Biblioteca Compartida (`shared/`)

Módulos comunes empaquetados para que puedan ser importados tanto por los microservicios del backend como por el runtime perimetral.

* **`shared/proto/`**: Archivos de definición de interfaz gRPC (`.proto`).
* **`shared/proto_gen/`**: Código Python autogenerado a partir de los archivos proto mediante `grpcio-tools`.
* **`shared/transport/`**: Envoltorios y clientes genéricos para el protocolo de red (por ejemplo, abstracciones de conexión MQTT seguras).
* **`shared/utils/`**:
  * `database.py`: Utilidades para arrancar sesiones SQLAlchemy y pools de bases de datos.
  * `minio.py`: Cliente y métodos de ayuda para interactuar con el almacenamiento en la nube MinIO S3 (creación de buckets, generación de URLs prefirmadas de descarga, carga de binarios).
  * `logging.py`: Configuración de formato y niveles de logs unificados para todo el sistema.

---

## 5. Hardware y Utilidades (`hardware/` & `scripts/`)

Módulos complementarios y de simulación.

* **`hardware/`**:
  * `sensors/` y `actuators/`: Interfaces de simulación para pruebas en local del agente sin hardware real conectado.
  * `hw_arch/`: Plantillas de compilación y optimizadores específicos para plataformas Raspberry Pi.
  * `utils.py`: Lecturas de bajo nivel del hardware (temperaturas de SOC, voltajes, etc.).
* **`scripts/`**:
  * Scripts en Bash y Python para pruebas unitarias de gRPC, simuladores de telemetría masiva y scripts de limpieza de bases de datos.
